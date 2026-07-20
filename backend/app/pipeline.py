"""
STEP1~STEP5 전체를 하나로 묶고, 데모 화면의 '실시간 스텝 인디케이터'용으로
각 단계가 끝날 때마다 SSE 이벤트를 흘려보냅니다.
"""
import json

from app.schemas import PlanRequest, ReplanRequest
from app.services import document_ai, agents, groundedness


async def run_pipeline_stream(req: PlanRequest):
    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    # STEP1~2. 입력 분석 (텍스트는 이미 구조화되어 들어온다고 가정,
    # 필요 시 여기서 document_ai.parse_text_constraints(req.prompt) 재검증 가능)
    yield sse("step", {"step": 1, "label": "입력 분석", "status": "running"})
    constraints = {
        "budget_krw": req.budget,
        "headcount": req.headcount,
        "transport": req.transport,
        "weather_sensitive": req.weather_sensitive,
        "mood_keywords": req.mood_keywords,
    }
    yield sse("step", {"step": 1, "label": "입력 분석", "status": "done"})

    # STEP4. 코스 설계 (Planner → Local-Expert → Critic → 최종 설명)
    yield sse("step", {"step": 2, "label": "코스 추론·생성", "status": "running"})
    anchor = req.anchor.model_dump() if req.anchor else None
    if anchor is None:
        yield sse("error", {"message": "앵커 장소가 필요합니다."})
        return
    must_include = req.must_include_place.model_dump() if req.must_include_place else None
    courses = await agents.plan_courses(constraints, anchor, must_include_place=must_include)
    yield sse("step", {"step": 2, "label": "코스 추론·생성", "status": "done"})

    # STEP5. 환각 검증
    yield sse("step", {"step": 3, "label": "환각 검증", "status": "running"})
    verified = []
    for course in courses:
        realtime_context = (
            f"{course['label']} 코스는 {len(course['places'])}개 장소로 구성되며 "
            f"총 이동거리 {course['total_distance_m']}m, "
            f"총 이동시간 {course['total_duration_min']}분입니다."
        )
        gr = groundedness.check_course_groundedness(realtime_context, course["reasoning"])
        verified.append({**course, **gr})
    yield sse("step", {"step": 3, "label": "환각 검증", "status": "done"})

    # STEP6. 결과 반환 (프론트는 이 이벤트로 지도 렌더링)
    yield sse("result", {"courses": verified})


async def replan_for_disruption(req: ReplanRequest) -> dict:
    """
    돌발 상황(비, 임시휴무 등) 발생 시 코스 재구성.
    - exclude_place_name: 문제가 된 그 장소만 다음 후보로 교체
    - disruption_reason에 '비'/'우천' 등이 있으면 weather_sensitive를 강제로 켜서
      Planner가 실내 위주로 다시 설계하도록 유도
    """
    original = req.original_plan_request
    constraints = {
        "budget_krw": original.budget,
        "headcount": original.headcount,
        "transport": original.transport,
        "weather_sensitive": original.weather_sensitive
        or any(kw in req.disruption_reason for kw in ["비", "우천", "폭우", "눈"]),
        "mood_keywords": original.mood_keywords,
    }
    anchor = original.anchor.model_dump() if original.anchor else None
    must_include = (
        original.must_include_place.model_dump() if original.must_include_place else None
    )
    exclude = [req.exclude_place_name] if req.exclude_place_name else []

    courses = await agents.plan_courses(
        constraints, anchor, must_include_place=must_include, exclude_place_names=exclude
    )
    return {"disruption_reason": req.disruption_reason, "courses": courses}
