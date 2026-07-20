"""
STEP 3 (파이프라인 기준 STEP5). 환각 검증.
카카오맵 실시간 데이터(영업여부/거리)를 context로,
Solar가 생성한 코스 설명을 answer로 넣어 grounded 여부를 판정합니다.
"""
from langchain_upstage import UpstageGroundednessCheck

from app.config import UPSTAGE_API_KEY

_checker = UpstageGroundednessCheck(upstage_api_key=UPSTAGE_API_KEY)


def check_course_groundedness(realtime_context: str, course_reasoning: str) -> dict:
    """
    realtime_context: 카카오 API로 확보한 실제 영업시간/거리/이동시간 등 사실 정보 텍스트
    course_reasoning: Solar가 생성한 코스에 대한 설명(검증 대상 answer)
    """
    result = _checker.invoke({"context": realtime_context, "answer": course_reasoning})
    grounded = str(result).lower().startswith("grounded")
    return {
        "grounded": grounded,
        "raw_result": str(result),
    }
