"""
프론트엔드(coursemate2.vercel.app)가 그대로 쓸 수 있는 계약:

요청: { "query": "자유 문장" }
응답: { "title": str, "courses": [ {id, title, description, duration, places:[...]} ] }
      또는 결과 없음: { "title": null, "courses": [], "message": "..." }

내부적으로는 기존 파이프라인(query_router → agents.plan_courses)을 그대로 재사용하고,
여기서는 '입력 받기 → 내부 형식으로 변환 → 내부 파이프라인 실행 → 프론트 계약으로 재포장'만 담당합니다.
"""
import asyncio
import json

from app.services import query_router, kakao, hours, reviews, groundedness


def _is_place_verified(place: dict) -> bool:
    """
    verified 판단 기준: (1) 근거가 된 리뷰가 실제로 있고, (2) 영업 상태가 '닫힘'이 아닐 것.
    두 신호 다 확보됐을 때만 true로, 확신 없는 정보는 false로 보수적으로 처리합니다.
    """
    has_review_evidence = bool(place.get("matched_review"))
    opening_status = (place.get("opening_status") or {}).get("status", "unknown")
    not_closed = opening_status != "closed" and not place.get("may_be_closed", False)
    return has_review_evidence and not_closed


def _format_duration(total_duration_min: float) -> str:
    hours_part = total_duration_min / 60
    if hours_part < 1:
        return f"약 {int(total_duration_min)}분"
    return f"약 {round(hours_part, 1)}시간"


def _groundedness_note(grounded: bool) -> str:
    return (
        "실제 영업시간·이동거리 데이터와 일치하는 설명이에요."
        if grounded
        else "설명 일부가 실제 데이터와 다를 수 있어 참고만 해주세요."
    )


async def _attach_groundedness(courses: list[dict]) -> list[dict]:
    """
    STEP5 환각 검증. 카카오 실시간 데이터(장소 수/이동거리/이동시간)를 context로,
    Solar가 생성한 코스 reasoning을 answer로 넣어 grounded 여부를 판정합니다.
    (기존엔 groundedness.check_course_groundedness가 구현만 되어 있고 실제 프론트가 쓰는
    /api/courses·/api/courses/stream 경로에는 연결이 안 되어 있었음 — 여기서 연결)
    """

    async def check(course: dict) -> None:
        realtime_context = (
            f"{course['label']} 코스는 {len(course['places'])}개 장소로 구성되며 "
            f"총 이동거리 {course['total_distance_m']}m, "
            f"총 이동시간 {course['total_duration_min']}분입니다."
        )
        # check_course_groundedness는 동기 함수(외부 API 호출)라 asyncio.to_thread로 돌려서
        # 코스 3개를 asyncio.gather로 동시에 검증(순차 호출 대비 응답 지연 감소).
        gr = await asyncio.to_thread(
            groundedness.check_course_groundedness, realtime_context, course["reasoning"]
        )
        course["grounded"] = gr["grounded"]
        course["groundedness_note"] = _groundedness_note(gr["grounded"])

    await asyncio.gather(*[check(c) for c in courses])
    return courses


def _to_frontend_course(
    course: dict,
    index: int,
    requirement_keywords: list[str],
    must_include_name: str | None = None,
) -> dict:
    places_out = []
    for p in course["places"]:
        matched = [
            kw for kw in requirement_keywords
            if p.get("matched_review") and reviews.keyword_matches(kw, p["matched_review"]["text"])
        ]
        places_out.append(
            {
                "name": p["name"],
                "lat": p["lat"],
                "lng": p["lng"],
                "hours": hours.format_hours_text(p["name"]),
                "verified": _is_place_verified(p),
                "matchedConstraints": matched,
                "reviewSnippet": (p.get("matched_review") or {}).get("text", ""),
                # SNS 캡처 이미지에서 인식·검증되어 must_include_place로 반영된 장소인지 표시
                "fromImage": bool(must_include_name) and p["name"] == must_include_name,
            }
        )

    return {
        "id": index + 1,
        "title": course["label"],
        "description": " → ".join(p["name"] for p in course["places"]),
        "duration": _format_duration(course["total_duration_min"]),
        "grounded": course.get("grounded"),
        "groundednessNote": course.get("groundedness_note"),
        "places": places_out,
    }


async def _resolve_anchor_and_constraints(parsed: dict):
    """
    parsed(query_router 출력)에서 지역 좌표를 실제로 찾고, Planner에 넘길 constraints/anchor를
    구성. 지역을 못 찾으면 None (호출부에서 '결과 없음' 응답으로 처리).
    """
    anchor_text = parsed.get("anchor_text") or "서울"
    anchor_coords = await kakao.geocode_district(anchor_text)
    if not anchor_coords:
        return None

    requirement_keywords = parsed.get("requirement_keywords") or []
    constraints = {
        "budget_krw": parsed.get("budget_krw"),
        "headcount": parsed.get("headcount"),
        "transport": parsed.get("transport"),
        "weather_sensitive": parsed.get("weather_sensitive", False),
        "mood_keywords": requirement_keywords + (
            [parsed["category_keyword"]] if parsed.get("category_keyword") else []
        ),
    }
    anchor = {"name": anchor_text, "lat": anchor_coords["lat"], "lng": anchor_coords["lng"]}
    return anchor_text, anchor, constraints, requirement_keywords


async def _generate_courses(
    parsed: dict,
    exclude_place_names: list[str] | None = None,
    must_include_place: dict | None = None,
) -> dict:
    """handle_free_query와 handle_replan이 공유하는 실행 로직."""
    from app.services import agents

    resolved = await _resolve_anchor_and_constraints(parsed)
    if resolved is None:
        anchor_text = parsed.get("anchor_text") or "서울"
        return {
            "title": None,
            "courses": [],
            "message": f"'{anchor_text}' 지역을 찾지 못했어요. 지역명을 다시 확인해주세요.",
        }
    anchor_text, anchor, constraints, requirement_keywords = resolved

    courses = await agents.plan_courses(
        constraints,
        anchor,
        must_include_place=must_include_place,
        seed_anchor_as_place=False,
        exclude_place_names=exclude_place_names or [],
    )
    courses = [c for c in courses if len(c["places"]) >= 2]

    if not courses:
        return {
            "title": None,
            "courses": [],
            "message": "조건에 맞는 코스를 찾지 못했어요. 조건을 조금 완화해서 다시 시도해보세요.",
        }

    courses = await _attach_groundedness(courses)
    must_include_name = must_include_place["name"] if must_include_place else None

    return {
        "title": f"{anchor_text} {parsed.get('category_keyword') or ''} 코스".strip(),
        "courses": [
            _to_frontend_course(c, i, requirement_keywords, must_include_name)
            for i, c in enumerate(courses)
        ],
    }


async def _generate_courses_stream(parsed: dict, must_include_place: dict | None = None):
    """
    _generate_courses와 같은 로직이되, agents.plan_courses의 실제 진행 상황을 SSE 이벤트로
    실시간 중계합니다. (프론트 STEP 로딩 인디케이터가 고정 타이머 대신 실제 백엔드 처리
    속도에 맞춰 갱신되도록 하기 위한 스트리밍 버전)
    """
    from app.services import agents

    def sse(event: str, data: dict) -> dict:
        # EventSourceResponse(main.py)에 dict를 그대로 yield하면 sse_starlette가 알아서
        # "event: ...\ndata: ...\n\n" 형식으로 인코딩함. 직접 문자열로 포맷해서 yield하면
        # (pipeline.py의 기존 방식) sse_starlette가 그 문자열 전체를 "data:" 한 줄로 또
        # 감싸버려서 이중으로 래핑되는 문제가 있어 이 방식을 씀.
        return {"event": event, "data": json.dumps(data, ensure_ascii=False)}

    yield sse("step", {"step": 1, "label": "사용자 입력을 분석하고 있어요..."})
    resolved = await _resolve_anchor_and_constraints(parsed)
    if resolved is None:
        anchor_text = parsed.get("anchor_text") or "서울"
        yield sse("result", {
            "title": None,
            "courses": [],
            "message": f"'{anchor_text}' 지역을 찾지 못했어요. 지역명을 다시 확인해주세요.",
        })
        return
    anchor_text, anchor, constraints, requirement_keywords = resolved

    # agents.plan_courses는 일반 코루틴이라 중간 진행 상황을 직접 yield할 수 없으므로,
    # 백그라운드 태스크로 돌리고 on_progress 콜백이 큐에 넣어주는 이벤트를 여기서 흘려보냅니다.
    queue: asyncio.Queue = asyncio.Queue()

    async def on_progress(step: int, label: str):
        await queue.put((step, label))

    async def run():
        try:
            return await agents.plan_courses(
                constraints,
                anchor,
                must_include_place=must_include_place,
                seed_anchor_as_place=False,
                on_progress=on_progress,
            )
        finally:
            await queue.put(None)  # 완료 신호

    task = asyncio.create_task(run())

    while True:
        item = await queue.get()
        if item is None:
            break
        step, label = item
        yield sse("step", {"step": step, "label": label})

    courses = await task
    courses = [c for c in courses if len(c["places"]) >= 2]

    if not courses:
        yield sse("result", {
            "title": None,
            "courses": [],
            "message": "조건에 맞는 코스를 찾지 못했어요. 조건을 조금 완화해서 다시 시도해보세요.",
        })
        return

    courses = await _attach_groundedness(courses)
    must_include_name = must_include_place["name"] if must_include_place else None

    yield sse("result", {
        "title": f"{anchor_text} {parsed.get('category_keyword') or ''} 코스".strip(),
        "courses": [
            _to_frontend_course(c, i, requirement_keywords, must_include_name)
            for i, c in enumerate(courses)
        ],
    })


async def handle_free_query(query: str, must_include_place: dict | None = None) -> dict:
    parsed = query_router.parse_free_query(query)
    return await _generate_courses(parsed, must_include_place=must_include_place)


async def handle_free_query_stream(query: str, must_include_place: dict | None = None):
    parsed = query_router.parse_free_query(query)
    async for chunk in _generate_courses_stream(parsed, must_include_place=must_include_place):
        yield chunk


async def handle_replan(query: str, disruption_reason: str, exclude_place_name: str | None = None) -> dict:
    """
    돌발 상황(비, 임시휴무 등) 발생 시 코스 재구성.
    - exclude_place_name: 문제가 된 그 장소만 다음 후보로 교체
    - disruption_reason에 '비'/'우천'/'눈' 등이 있으면 weather_sensitive를 강제로 켜서
      Planner가 실내 위주로 다시 설계하도록 유도
    """
    parsed = query_router.parse_free_query(query)
    if any(kw in disruption_reason for kw in ["비", "우천", "폭우", "눈"]):
        parsed["weather_sensitive"] = True

    exclude = [exclude_place_name] if exclude_place_name else []
    result = await _generate_courses(parsed, exclude_place_names=exclude)
    result["disruption_reason"] = disruption_reason
    return result
