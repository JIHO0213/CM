"""
STEP 3 (파이프라인 기준 STEP5). 환각 검증.
카카오맵 실시간 데이터(영업여부/거리)를 context로,
Solar가 생성한 코스 설명을 answer로 넣어 grounded 여부를 판정합니다.

주의: langchain_upstage.UpstageGroundednessCheck는 Upstage가 이미 서비스 종료한 전용 모델
(solar-1-mini-answer-verification)을 내부에 하드코딩하고 있어서, 지금 호출하면 항상
"The requested model is invalid or no longer supported" 400 에러가 납니다(실제 호출해서 확인함).
그 대체 모델명(solar-1-mini-groundedness-check)도 이 계정/API 버전에서는 동일하게 거부됩니다.
그래서 전용 모델 대신, 이미 다른 곳(query_router/agents/document_ai)에서 정상 동작이 검증된
범용 Solar 모델(SOLAR_MODEL)에게 "answer가 context에 근거하는가"를 grounded/notGrounded
둘 중 하나로만 답하도록 시켜서 같은 역할을 대신합니다.
"""
from openai import OpenAI

from app.config import UPSTAGE_API_KEY, UPSTAGE_BASE_URL, SOLAR_MODEL

client = OpenAI(api_key=UPSTAGE_API_KEY, base_url=UPSTAGE_BASE_URL)

_SYSTEM_PROMPT = (
    "당신은 answer가 context에 실제로 근거하는지 판정하는 채점자입니다. "
    "context에 없는 사실을 answer가 지어냈다면 notGrounded, context와 일치하거나 "
    "context를 벗어나지 않는 범위의 설명이면 grounded로 판정하세요. "
    "다른 말이나 설명 없이 grounded 또는 notGrounded 중 하나만 정확히 출력하세요."
)


def check_course_groundedness(realtime_context: str, course_reasoning: str) -> dict:
    """
    realtime_context: 카카오 API로 확보한 실제 영업시간/거리/이동시간 등 사실 정보 텍스트
    course_reasoning: Solar가 생성한 코스에 대한 설명(검증 대상 answer)
    """
    completion = client.chat.completions.create(
        model=SOLAR_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"context: {realtime_context}\nanswer: {course_reasoning}"},
        ],
        temperature=0,
    )
    result = (completion.choices[0].message.content or "").strip()
    grounded = result.lower().startswith("grounded")
    return {
        "grounded": grounded,
        "raw_result": result,
    }
