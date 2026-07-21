"""
STEP 4. 코스 설계 — Solar LLM Multi-Agent Orchestration.

주의: 업스테이지가 제공하는 '멀티에이전트 API'는 없습니다. 아래는 Solar Chat을
서로 다른 system prompt(역할)로 순차 호출하며, Local-Expert 단계에서만
카카오 API를 실제로 호출하는 우리 서버 쪽 오케스트레이션 로직입니다.

흐름: Planner(코스 컨셉 초안) → Local-Expert(카카오 API + 리뷰 + 영업여부로 실장소 확정)
      → Critic(제약조건 위반 여부 검토) → 최종 설명 생성(실제 데이터 기반 이유/상황 설명)
"""
import asyncio
import json

from openai import OpenAI

from app.config import UPSTAGE_API_KEY, UPSTAGE_BASE_URL, SOLAR_MODEL
from app.services import kakao, reviews, hours, share
from app.services.json_utils import extract_json

client = OpenAI(api_key=UPSTAGE_API_KEY, base_url=UPSTAGE_BASE_URL)


PLANNER_PROMPT = """당신은 데이트/모임 코스를 기획하는 Planner Agent입니다.
주어진 제약조건과 앵커 장소를 바탕으로, 서로 성격이 다른 코스 컨셉 3개를 설계하세요.
각 코스는 앵커 장소를 포함해 2~5개의 정거장(카테고리+무드 키워드만, 실제 상호명은 아직 몰라도 됨)으로
구성합니다. 정거장 개수를 항상 3개로 고정하지 말고, 제약조건(예산·인원·이동시간·날씨 민감도)과
코스 컨셉에 맞게 유동적으로 정하세요 — 가볍게 들르는 코스는 2~3개, 하루 알차게 도는 코스는
4~5개처럼 코스마다 달라도 됩니다.
만약 constraints.must_include_place가 있다면, 그 장소는 반드시 모든 코스에 정거장으로 포함시키고
category_keyword 대신 "__must_include__"라고만 적으세요.

만약 constraints.required_categories(배열)가 있다면, 그 배열 안의 항목 각각은 사용자가 명시적으로
요청한 장소 종류이므로 "전부" 모든 코스에 최소 하나의 정거장으로 반드시 포함시키세요. 예를 들어
required_categories가 ["한식", "팝업스토어"]라면, 코스마다 한식 관련 정거장 최소 1개와 팝업스토어
관련 정거장 최소 1개가 함께 있어야 하며, 둘 중 하나라도 빠뜨리면 안 됩니다. 이때 category_keyword는
그 요구사항을 그대로 베끼지 말고 카카오 검색에 맞는 구체적인 키워드로 바꾸세요
(예: required_categories의 "한식" -> category_keyword "한정식" 또는 "한식당").

정거장마다 "type"을 아래 3가지 중 하나로 반드시 지정하세요:
- "식당": 밥/식사 위주 (파스타, 곱창, 브런치 등)
- "카페": 커피·디저트·음료 위주
- "액티비티": 먹는 곳이 아니라 구경/체험하는 곳 (팝업스토어, 편집샵, 빈티지샵, 전시/갤러리,
  소품샵, 독립서점, 사진관, 공방, 방탈출 등)

진짜 데이트 코스처럼 성격이 다른 장소가 번갈아 나오게 짜고, 같은 type을 두 번 연속
배치하지 마세요 (예: 식당→식당 금지). 이상적인 흐름 예시: 식당→카페→액티비티,
카페→액티비티→식당, 액티비티→식당→카페 등. 정거장이 4~5개로 늘어나면 식당→카페→
액티비티→카페→식당처럼 두 번째 바퀴를 돌리되, 이때도 바로 앞 정거장과 같은 type만
피하면 됩니다.

category_keyword는 카카오 로컬 API에 그대로 검색어로 들어갑니다. 카카오 키워드 검색은
"카페", "반려동물 동반 카페", "빈티지샵"처럼 짧은 명사(구)일 때만 결과가 나오고,
지역명이나 제약조건 문장을 길게 욱여넣으면(예: "반려동물 동반 가능한 성수동 감성 카페
추천") 검색 결과가 0건이 됩니다. 지역은 이미 좌표로 주어지므로 keyword에 동네 이름을
다시 넣지 마세요. 조건은 정말 검색에 필요한 것 1개만 짧게 붙이세요.
  - 좋음: "카페", "반려동물 동반 카페", "브런치", "빈티지샵", "조용한 파스타"
  - 나쁨: "반려동물 동반 가능한 성수동 감성 카페 추천", "유모차로 이동하기 편한 브런치 맛집"

반드시 아래 JSON 배열 형식으로만 답하세요: (마지막 항목 뒤에 쉼표를 붙이지 마세요)
[
  {
    "course_id": "A",
    "label": "코스 성격 (예: 최단거리/감성 충만/가성비)",
    "stops": [
      {"order": 1, "type": "식당", "category_keyword": "카카오 로컬 검색에 쓸 짧은 키워드, 예: '조용한 파스타'"},
      {"order": 2, "type": "액티비티", "category_keyword": "예: '빈티지샵'"},
      {"order": 3, "type": "카페", "category_keyword": "..."}
    ],
    "reasoning": "이 코스를 이렇게 짠 이유 (초안, 나중에 실제 데이터로 다시 다듬어짐)"
  },
  ...
]
"""

CRITIC_PROMPT = """당신은 Critic Agent입니다. 아래 코스들이 제약조건
(예산/이동시간/날씨 민감도)을 위반하지 않는지 검토하고,
각 코스에 대해 "ok" 또는 "위반 사유"를 JSON으로 답하세요. (마지막 항목 뒤에 쉼표를 붙이지 마세요)

반드시 아래 형식으로만 답하세요:
{"A": "ok", "B": "예산 초과", "C": "ok"}
"""

FINAL_EXPLAIN_PROMPT = """당신은 완성된 코스에 대해 심사위원/사용자에게 설명하는
역할입니다. 아래에는 실제로 확정된 장소, 거리·시간, 참고한 리뷰, 영업 상태가
주어집니다. 이 실제 데이터에 근거해서만 설명하고, 데이터에 없는 내용은 지어내지 마세요.

각 코스에 대해 아래 JSON 형식으로만 답하세요: (마지막 항목 뒤에 쉼표를 붙이지 마세요)
{
  "A": {
    "reasoning": "이 코스를 추천하는 이유 (실제 장소명·리뷰·거리 언급, 2문장 이내)",
    "best_for": "이 코스가 어떤 상황에 적합한지 (예: '비 오는 날 조용한 실내 데이트에 적합', 1문장)"
  },
  ...
}
"""


def _diversify_stop_types(stops: list[dict]) -> list[dict]:
    """
    Planner가 프롬프트 지시를 안 지키고 같은 type(예: 식당-식당)을 연달아 배치했을 경우를
    대비한 서버 사이드 안전망. 실제 장소를 확정하기 전에(Local-Expert 단계 이전) 순서만
    바로잡습니다. must_include_place 정거장이 섞여 있으면 위치가 사용자 제약과 얽혀있을 수
    있으니 건드리지 않고 그대로 둡니다.
    """
    if not stops or any(s.get("category_keyword") == "__must_include__" for s in stops):
        return stops

    groups: dict[str, list[dict]] = {}
    for s in stops:
        groups.setdefault(s.get("type", "기타"), []).append(s)

    type_order = sorted(groups, key=lambda t: -len(groups[t]))
    result: list[dict] = []
    last_type = None
    remaining = len(stops)
    pointer = 0
    while remaining > 0:
        for offset in range(len(type_order)):
            t = type_order[(pointer + offset) % len(type_order)]
            bucket = groups[t]
            if bucket and t != last_type:
                result.append(bucket.pop(0))
                last_type = t
                remaining -= 1
                pointer = (pointer + offset + 1) % len(type_order)
                break
        else:
            # 어떤 type을 골라도 직전과 같을 수밖에 없는 경우(type 종류가 부족함):
            # 더 이상 개선 불가하므로 남은 정거장을 그대로 이어붙이고 종료.
            for t in type_order:
                result.extend(groups[t])
                groups[t] = []
            remaining = 0

    for i, s in enumerate(result, start=1):
        s["order"] = i
    return result


def _call_solar_json(system_prompt: str, user_content: str) -> dict | list:
    completion = client.chat.completions.create(
        model=SOLAR_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.4,
    )
    raw = completion.choices[0].message.content
    return extract_json(raw)


async def _choose_open_place(
    candidates: list[dict], mood_keywords: list[str], already_chosen: set[str] | None = None
) -> dict:
    """
    리뷰 매칭 순위대로 순서대로 보면서, '영업 중' 또는 '정보 없음'인 첫 후보를 채택.
    같은 코스 안에서 이미 선택된 장소(already_chosen)는 후보에서 제외해서,
    한 코스에 같은 장소가 두 번 들어가는 걸 방지합니다.
    전부 닫혀 있으면 1순위를 그대로 쓰되 may_be_closed=True로 표시(발표 중 빈 코스보다
    낫다는 판단, 실제 서비스라면 사용자에게 재검색을 유도하는 편이 더 낫습니다).
    """
    already_chosen = already_chosen or set()
    candidates = [c for c in candidates if c["name"] not in already_chosen]
    if not candidates:
        return {}

    ranked = reviews.rank_places(candidates, mood_keywords)
    fallback = None
    for place in ranked:
        status = hours.is_open_now(place["name"])
        place["opening_status"] = status
        if fallback is None:
            fallback = place
        if status["status"] in ("open", "unknown"):
            return place
    fallback["may_be_closed"] = True
    return fallback


async def _search_kakao_with_fallback(
    category_keyword: str,
    lng: float,
    lat: float,
    known_names: set[str],
    exclude_place_names: list[str],
) -> list[dict]:
    """
    카카오 로컬 키워드 검색은 짧은 명사(구)일 때만 결과가 나오고, Planner가 (프롬프트
    지시를 못 지켜서) "반려동물 동반 가능한 성수동 감성 카페"처럼 지역·조건을 욱여넣은
    긴 문장을 keyword로 주면 0건이 나옵니다. 그 경우 뒤쪽 1~2단어(보통 실제 카테고리
    명사가 옴, 예: "...감성 카페" -> "카페")만 남겨서 한 번 더 시도합니다.

    주의: 예전엔 "결과가 하나라도 있으면" 바로 반환했는데, 그러면 중간 길이 키워드(예:
    "현대 미술 갤러리" -> "미술 갤러리")가 큐레이션 안 된 엉뚱한 장소를 몇 건 찾아버리는
    순간 거기서 멈춰버려서, 정작 맞는 곳을 찾을 수 있었던 더 짧은 키워드("갤러리")까지는
    가보지도 못하고 실패하는 경우가 있었습니다(홍대처럼 큐레이션된 곳이 적은 지역에서
    특히 두드러짐). 그래서 지금은 "우리 가게 데이터에 있는 곳이 나올 때까지" 계속 좁혀서
    시도하고, 끝까지 하나도 못 찾으면 그나마 마지막으로 받은 결과를 반환합니다.
    """
    def has_known_match(cands: list[dict]) -> bool:
        return any(c["name"] in known_names and c["name"] not in exclude_place_names for c in cands)

    keywords_to_try = [category_keyword]
    tokens = category_keyword.split()
    if len(tokens) > 1:
        for n in (2, 1):
            shortened = " ".join(tokens[-n:])
            if shortened not in keywords_to_try:
                keywords_to_try.append(shortened)

    last_candidates: list[dict] = []
    for kw in keywords_to_try:
        candidates = await kakao.search_places(kw, lng, lat)
        if candidates:
            last_candidates = candidates
        if has_known_match(candidates):
            return candidates
    return last_candidates


async def _build_one_course(
    course: dict,
    constraints: dict,
    anchor: dict,
    must_include_place: dict | None,
    exclude_place_names: list[str],
    seed_anchor_as_place: bool,
) -> dict:
    """코스 1개를 완성(Local-Expert 단계). asyncio.gather로 코스 3개를 동시에 처리하기 위해 분리."""
    mood_keywords = constraints.get("mood_keywords") or []

    places = [anchor] if seed_anchor_as_place else []
    prev = anchor
    for stop in course.get("stops") or []:
        # Planner(Solar)가 가끔 프롬프트 형식을 안 지키고 category_keyword를 통째로 빼먹은
        # stop을 줄 때가 있음 — 그런 경우 이 정거장만 건너뛰고(코스 전체는 계속 진행) 죽지 않게 함
        category_keyword = stop.get("category_keyword")
        if not category_keyword:
            continue

        if category_keyword == "__must_include__" and must_include_place:
            places.append(must_include_place)
            prev = must_include_place
            continue

        # 데모 특성상 리뷰/영업시간 데이터가 준비된 장소만 노출(무작위 실제 장소가 나오면
        # 리뷰 없이 기본 문구만 뜨는 걸 방지). 카카오 검색 자체는 계속 실시간으로 하되,
        # 결과를 우리 데이터셋에 있는 이름으로만 걸러냅니다. (known_names를 검색 이전에
        # 미리 구해서 _search_kakao_with_fallback에 넘겨줘야, 그 안에서 "우리 데이터에
        # 있는 곳이 나올 때까지" 키워드를 계속 좁혀볼 수 있음)
        known_names = reviews.known_place_names()
        candidates = await _search_kakao_with_fallback(
            category_keyword, prev["lng"], prev["lat"], known_names, exclude_place_names
        )
        candidates = [
            c for c in candidates
            if c["name"] in known_names and c["name"] not in exclude_place_names
        ]
        if not candidates:
            # Planner가 준 세부 키워드(예: "조용한 파스타")가 너무 구체적이라 큐레이션된
            # 82곳 중 아무 것도 안 걸렸을 수 있음 → 정거장을 통째로 포기하기 전에, 같은
            # type의 대분류 키워드로 한 번 더 검색해서 큐레이션 데이터 안에서 채워봄
            # (여전히 known_names로만 거르므로 검증 안 된 장소는 노출 안 됨).
            generic_keyword = {"식당": "맛집", "카페": "카페", "액티비티": "전시"}.get(
                stop.get("type")
            )
            if generic_keyword and generic_keyword != category_keyword:
                retry = await _search_kakao_with_fallback(
                    generic_keyword, prev["lng"], prev["lat"], known_names, exclude_place_names
                )
                candidates = [
                    c for c in retry
                    if c["name"] in known_names and c["name"] not in exclude_place_names
                ]
        if not candidates:
            continue
        already_chosen_names = {p["name"] for p in places}
        chosen = await _choose_open_place(candidates, mood_keywords, already_chosen_names)
        if not chosen:
            # 이 코스에서 이미 선택된 장소뿐이라 새로 고를 후보가 없음 → 이 정거장은 건너뜀
            continue
        places.append(chosen)
        prev = chosen

    total_distance, total_duration = 0.0, 0.0
    for i in range(len(places) - 1):
        route = await kakao.get_route(places[i], places[i + 1])
        total_distance += route["distance_m"]
        total_duration += route["duration_min"]

    return {
        "course_id": course.get("course_id", "?"),
        "label": course.get("label", "추천 코스"),
        "places": places,
        "total_distance_m": round(total_distance, 1),
        "total_duration_min": round(total_duration, 1),
        "reasoning": course.get("reasoning", ""),  # 아래에서 실제 데이터 기반으로 덮어씀
    }


async def plan_courses(
    constraints: dict,
    anchor: dict,
    must_include_place: dict | None = None,
    exclude_place_names: list[str] | None = None,
    seed_anchor_as_place: bool = True,
    on_progress=None,
) -> list[dict]:
    """
    seed_anchor_as_place=False: anchor가 실제 방문 장소가 아니라 '지역 중심 좌표'일 때
    (자유 텍스트 쿼리에서 동네 이름만 뽑아낸 경우). 이 경우 anchor는 검색 시작 기준점으로만
    쓰이고, 최종 places 목록에는 포함되지 않습니다.

    on_progress: 각 단계(Planner/Local-Expert, Critic, 최종 설명)가 시작될 때 호출되는
    선택적 콜백(async def on_progress(step: int, label: str)). 로딩 UI를 실제 진행 상황에
    맞춰 실시간으로 갱신하려는 스트리밍 엔드포인트(course_contract._generate_courses_stream)를
    위한 훅이고, 지정 안 하면(None) 기존 호출부(pipeline.py 등)는 아무 영향 없습니다.
    """
    exclude_place_names = exclude_place_names or []

    # 이미지에서 인식된 장소라도, 우리 가게 데이터(리뷰/영업시간이 준비된 82곳)에 없으면
    # 검증되지 않은 장소이므로 코스에 강제로 넣지 않습니다. (SNS 캡처 반영 기능의 안전장치)
    if must_include_place and must_include_place.get("name") not in reviews.known_place_names():
        must_include_place = None

    async def emit(step: int, label: str):
        if on_progress:
            await on_progress(step, label)

    # --- Planner ---
    await emit(2, "주변 인기 장소를 검색하고 있어요...")
    planner_constraints = dict(constraints)
    if must_include_place:
        planner_constraints["must_include_place"] = must_include_place["name"]
    planner_input = json.dumps(
        {"constraints": planner_constraints, "anchor": anchor}, ensure_ascii=False
    )
    draft_courses = _call_solar_json(PLANNER_PROMPT, planner_input)
    for course in draft_courses:
        if isinstance(course, dict) and isinstance(course.get("stops"), list):
            course["stops"] = _diversify_stop_types(course["stops"])

    # --- Local-Expert: 코스 3개를 동시에(병렬) 처리해서 응답 시간 단축 ---
    enriched = await asyncio.gather(
        *[
            _build_one_course(
                course, constraints, anchor, must_include_place, exclude_place_names, seed_anchor_as_place
            )
            for course in draft_courses
        ]
    )
    enriched = list(enriched)
    await emit(3, "이동 거리와 소요 시간을 계산하고 있어요...")

    # --- Critic ---
    await emit(4, "최적의 동선을 조합하고 있어요...")
    critic_input = json.dumps(
        {"constraints": constraints, "courses": enriched}, ensure_ascii=False
    )
    try:
        verdicts = _call_solar_json(CRITIC_PROMPT, critic_input)
        if not isinstance(verdicts, dict):
            raise ValueError(f"Critic 응답이 JSON 객체가 아닙니다: {type(verdicts).__name__}")
    except ValueError as e:
        print(f"[경고] Critic 응답 파싱 실패, 전부 'ok'로 간주하고 진행합니다: {e}")
        verdicts = {}
    for course in enriched:
        course["critic_verdict"] = verdicts.get(course["course_id"], "ok")

    # --- 최종 설명 생성 (실제 확정 데이터 기반 reasoning + best_for) ---
    await emit(5, "맞춤 코스를 완성했어요!")
    explain_input = json.dumps(
        {
            "constraints": constraints,
            "courses": [
                {
                    "course_id": c["course_id"],
                    "label": c["label"],
                    "places": [
                        {
                            "name": p["name"],
                            "matched_review": p.get("matched_review"),
                            "opening_status": p.get("opening_status"),
                        }
                        for p in c["places"]
                    ],
                    "total_distance_m": c["total_distance_m"],
                    "total_duration_min": c["total_duration_min"],
                }
                for c in enriched
            ],
        },
        ensure_ascii=False,
    )
    try:
        explanations = _call_solar_json(FINAL_EXPLAIN_PROMPT, explain_input)
        if not isinstance(explanations, dict):
            raise ValueError(f"최종 설명 응답이 JSON 객체가 아닙니다: {type(explanations).__name__}")
    except ValueError as e:
        # 최종 설명은 부가 정보(reasoning/best_for)일 뿐 코스 자체는 이미 확정된 상태이므로,
        # Solar가 거부/파싱 불가 응답을 주더라도 전체 요청을 500으로 실패시키지 않고
        # Planner 단계의 초안 reasoning을 그대로 유지한 채 진행합니다.
        print(f"[경고] 최종 설명 생성 실패, 초안 reasoning으로 대체합니다: {e}")
        explanations = {}
    for course in enriched:
        exp = explanations.get(course["course_id"], {})
        course["reasoning"] = exp.get("reasoning", course["reasoning"])
        course["best_for"] = exp.get("best_for", "")

    # --- 공유/예약/딥링크 데이터 첨부 ---
    for course in enriched:
        course["navi_deeplink"] = kakao.build_navi_deeplink(course["places"])
        course["share_payload"] = share.build_share_payload(course)
        course["reservations"] = [
            {"place_name": p["name"], **share.build_reservation_info(p)}
            for p in course["places"]
            if p.get("place_url") or p.get("phone")
        ]

    return enriched
