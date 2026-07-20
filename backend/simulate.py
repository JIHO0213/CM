"""
실제 서버를 띄운 것처럼 /api/courses, /api/courses/replan 등에 진짜 HTTP 요청을 보내서
동작을 검증하는 시뮬레이션 스크립트.

업스테이지(Solar LLM)와 카카오 API만 가짜 응답으로 대체하고, 그 외 모든 로직
(Planner→Local-Expert→Critic→최종설명, 리뷰/영업여부 매칭, 프론트 계약 변환,
에러 처리, CORS)은 실제 코드를 그대로 실행합니다.
"""
import os
import sys
import json
from unittest.mock import patch, AsyncMock, MagicMock

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

os.environ.setdefault("UPSTAGE_API_KEY", "dummy")
os.environ.setdefault("KAKAO_REST_API_KEY", "dummy")
sys.path.insert(0, ".")

# ---------------------------------------------------------------------------
# 1) 카카오 API 가짜 응답
# ---------------------------------------------------------------------------
FAKE_PLACES = [
    {"name": "프렌즈앤야드", "address": "서울 성동구", "lat": 37.5445, "lng": 127.0565,
     "category": "음식점 > 브런치", "phone": "02-1234-5678", "place_url": "http://place.kakao.com/1"},
    {"name": "카페 차", "address": "서울 성동구", "lat": 37.5450, "lng": 127.0570,
     "category": "카페", "phone": "", "place_url": "http://place.kakao.com/2"},
    {"name": "성수연방", "address": "서울 성동구", "lat": 37.5440, "lng": 127.0560,
     "category": "문화,예술 > 복합문화공간", "phone": "", "place_url": "http://place.kakao.com/3"},
]

async def fake_search_places(query, lng, lat, radius=1500):
    print(f"  [kakao.search_places 호출] query={query!r}")
    # type을 반영한 category_keyword에 맞춰 그럴듯한 후보만 돌려줘서,
    # 최종 코스 설명(A → B → C)에서 식당/카페/액티비티가 실제로 번갈아 나오는지 눈으로 확인 가능하게 함.
    if any(kw in query for kw in ("팝업", "빈티지", "편집", "전시", "액티비티")):
        return [FAKE_PLACES[2]]
    if "카페" in query:
        return [FAKE_PLACES[1]]
    return [FAKE_PLACES[0]]

async def fake_geocode_district(name):
    print(f"  [kakao.geocode_district 호출] name={name!r}")
    return {"lat": 37.5445, "lng": 127.0565, "address": name}

async def fake_get_route(origin, destination):
    return {"distance_m": 350.0, "duration_min": 5.0, "source": "fake"}


# ---------------------------------------------------------------------------
# 2) Solar LLM 가짜 응답 (호출되는 프롬프트 내용에 따라 다른 JSON을 돌려줌)
# ---------------------------------------------------------------------------
def make_fake_chat_completion(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    completion = MagicMock()
    completion.choices = [choice]
    return completion


def fake_solar_dispatch(*args, **kwargs):
    messages = kwargs.get("messages", [])
    system_content = messages[0]["content"] if messages else ""

    if "지역/동네 이름" in system_content:
        # query_router.parse_free_query
        content = json.dumps({
            "anchor_text": "성수동",
            "category_keyword": "브런치",
            "requirement_keywords": ["유모차 진입 가능", "반려동물 동반"],
            "budget_krw": None, "headcount": None, "transport": None,
            "weather_sensitive": False,
        }, ensure_ascii=False)
        print("  [Solar 호출] query_router.parse_free_query 역할")

    elif "Planner Agent" in system_content:
        content = json.dumps([
            # 일부러 식당→식당→카페(연속 '식당') 순서로 줘서, 서버 사이드
            # _diversify_stop_types가 실제로 재배치하는지 end-to-end로 검증.
            {"course_id": "A", "label": "유모차 프렌들리 브런치 코스",
             "stops": [{"order": 1, "type": "식당", "category_keyword": "브런치"},
                       {"order": 2, "type": "식당", "category_keyword": "파스타"},
                       {"order": 3, "type": "카페", "category_keyword": "카페"}],
             "reasoning": "초안 이유"},
            {"course_id": "B", "label": "감성 충만 코스",
             "stops": [{"order": 1, "category_keyword": "브런치"}],
             "reasoning": "초안 이유2"},
            {"course_id": "C", "label": "가성비 코스",
             "stops": [{"order": 1, "category_keyword": "카페"}],
             "reasoning": "초안 이유3"},
        ], ensure_ascii=False)
        print("  [Solar 호출] Planner 역할")

    elif "Critic Agent" in system_content:
        # 실제로 겪었던 버그를 재현: Solar가 첫 JSON(오답)을 쓰고, 반성 문단을 쓴 뒤
        # "수정된 답변"이라며 두 번째(진짜) JSON을 또 붙이는 경우
        content = """{"A": "ok", "B": "채식 가능", "C": "반려동물 출입 가능"}

(※ 주의: 주어진 제약조건에서 "mood_keywords"는 필수 조건이지만, "위반 사유" 대신
해당 키워드가 충족되었음을 나타내는 방식으로 답변해야 합니다. 그러나 문제 지시사항에
따라 "ok" 또는 "위반 사유"만 반환해야 하므로, 아래 수정된 답변을 참고하세요.)

**수정된 답변**:
{"A": "ok", "B": "ok", "C": "ok"}"""
        print("  [Solar 호출] Critic 역할 (일부러 '자기수정으로 JSON 2개' 패턴을 넣어서 복구 로직 테스트)")

    elif "완성된 코스에 대해" in system_content:
        # 실제로 겪었던 trailing comma 버그를 재현: 마지막 항목 뒤에 쉼표를 일부러 붙임
        content = """{
  "A": {"reasoning": "실제 리뷰 기반 이유", "best_for": "유모차 동반 브런치에 적합"},
  "B": {"reasoning": "실제 리뷰 기반 이유2", "best_for": "감성 데이트에 적합"},
  "C": {"reasoning": "실제 리뷰 기반 이유3", "best_for": "가성비 모임에 적합"},
}"""
        print("  [Solar 호출] 최종 설명 생성 역할 (일부러 trailing comma를 넣어서 복구 로직 테스트)")

    else:
        content = "{}"
        print("  [Solar 호출] 알 수 없는 프롬프트 (기본값 반환)")

    return make_fake_chat_completion(content)


print("=" * 70)
print("시뮬레이션 시작: POST /api/courses")
print("=" * 70)

with patch("app.services.kakao.search_places", new=AsyncMock(side_effect=fake_search_places)), \
     patch("app.services.kakao.geocode_district", new=AsyncMock(side_effect=fake_geocode_district)), \
     patch("app.services.kakao.geocode_address", new=AsyncMock(return_value=None)), \
     patch("app.services.kakao.get_route", new=AsyncMock(side_effect=fake_get_route)), \
     patch("app.services.agents.client.chat.completions.create", side_effect=fake_solar_dispatch), \
     patch("app.services.query_router.client.chat.completions.create", side_effect=fake_solar_dispatch):

    from fastapi.testclient import TestClient
    import app.main as m

    client = TestClient(m.app)

    res = client.post(
        "/api/courses",
        json={"query": "성수동에서 유모차 진입 가능하고 반려동물 동반되는 브런치 코스"},
        headers={"Origin": "http://localhost:5173"},
    )

    print("\n--- 응답 ---")
    print("status_code:", res.status_code)
    print("CORS 헤더(access-control-allow-origin):", res.headers.get("access-control-allow-origin"))
    data = res.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))

    # ---- 검증 ----
    assert res.status_code == 200, "정상 요청인데 200이 아님"
    assert "title" in data and "courses" in data, "응답 최상위 키 누락"
    assert len(data["courses"]) >= 1, "코스가 하나도 안 나옴"
    course0 = data["courses"][0]
    for key in ("id", "title", "description", "duration", "places"):
        assert key in course0, f"course에 '{key}' 필드 누락"
    place0 = course0["places"][0]
    for key in ("name", "lat", "lng", "hours", "verified", "matchedConstraints", "reviewSnippet"):
        assert key in place0, f"place에 '{key}' 필드 누락"

    print("\n✅ /api/courses 검증 통과 (필드 구조, JSON 파싱 모두 정상)")

print()
print("=" * 70)
print("시뮬레이션: POST /api/courses/replan (돌발 상황)")
print("=" * 70)

with patch("app.services.kakao.search_places", new=AsyncMock(side_effect=fake_search_places)), \
     patch("app.services.kakao.geocode_district", new=AsyncMock(side_effect=fake_geocode_district)), \
     patch("app.services.kakao.geocode_address", new=AsyncMock(return_value=None)), \
     patch("app.services.kakao.get_route", new=AsyncMock(side_effect=fake_get_route)), \
     patch("app.services.agents.client.chat.completions.create", side_effect=fake_solar_dispatch), \
     patch("app.services.query_router.client.chat.completions.create", side_effect=fake_solar_dispatch):

    from fastapi.testclient import TestClient
    import importlib
    import app.main as m
    importlib.reload(m)
    client = TestClient(m.app)

    res = client.post(
        "/api/courses/replan",
        json={
            "query": "성수동에서 유모차 진입 가능하고 반려동물 동반되는 브런치 코스",
            "disruption_reason": "갑자기 비가 와요",
        },
    )
    print("status_code:", res.status_code)
    data = res.json()
    print(json.dumps(data, ensure_ascii=False, indent=2)[:500], "...(생략)")
    assert res.status_code == 200
    assert "disruption_reason" in data
    print("\n✅ /api/courses/replan 검증 통과")

print()
print("=" * 70)
print("시뮬레이션: 서버 내부 에러 발생 시 CORS 헤더가 살아있는지 확인")
print("=" * 70)

def raise_error(*args, **kwargs):
    raise RuntimeError("일부러 발생시킨 테스트용 에러")

with patch("app.services.course_contract.handle_free_query", side_effect=raise_error):
    from fastapi.testclient import TestClient
    import importlib
    import app.main as m
    importlib.reload(m)
    client = TestClient(m.app)

    res = client.post(
        "/api/courses",
        json={"query": "아무 문장"},
        headers={"Origin": "http://localhost:5173"},
    )
    print("status_code:", res.status_code)
    print("CORS 헤더:", res.headers.get("access-control-allow-origin"))
    print("응답 본문:", res.json())

    assert res.status_code == 500, "에러 상황인데 500이 아님"
    assert res.headers.get("access-control-allow-origin") is not None, \
        "CORS 헤더가 없음! (예전에 겪었던 그 버그가 재발한 것)"
    assert "error" in res.json()
    print("\n✅ 에러 상황에서도 CORS 헤더 정상 (예전 버그 재발 없음)")

print()
print("=" * 70)
print("모든 시뮬레이션 통과 ✅")
print("=" * 70)
