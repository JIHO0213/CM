"""
프론트에서 오는 { "query": "자유 문장" } 하나를 받아서, 코스 생성에 필요한
모든 조건(지역, 카테고리, 필수 요구사항 키워드, 예산 등)을 한번에 뽑아내는 파서.
"""
from openai import OpenAI

from app.config import UPSTAGE_API_KEY, UPSTAGE_BASE_URL, SOLAR_MODEL
from app.services.json_utils import extract_json

client = OpenAI(api_key=UPSTAGE_API_KEY, base_url=UPSTAGE_BASE_URL)

PARSE_PROMPT = """사용자의 한 문장 요청에서 코스 추천에 필요한 정보를 뽑아내세요.
반드시 아래 JSON 형식으로만 답하세요. 설명은 붙이지 마세요. (마지막 항목 뒤에 쉼표를 붙이지 마세요)

{
  "anchor_text": "지역/동네 이름 (예: '성수동'). 없으면 null",
  "category_keywords": ["찾는 장소 종류를 전부 배열로. 사용자가 '한식 먹고 팝업스토어 가고 싶어'처럼
    서로 다른 종류를 여러 개 언급했으면 빠짐없이 각각 항목으로 넣으세요
    (예: ['한식', '팝업스토어']). 하나만 언급했으면 항목 1개짜리 배열(예: ['브런치']).
    아무것도 안 언급했으면 빈 배열 []"],
  "requirement_keywords": ["사용자가 명시한 필수 조건들을 짧은 키워드로. 예: '유모차 진입 가능', '반려동물 동반'"],
  "budget_krw": null,
  "headcount": null,
  "transport": null,
  "weather_sensitive": false
}
"""


def parse_free_query(query: str) -> dict:
    completion = client.chat.completions.create(
        model=SOLAR_MODEL,
        messages=[
            {"role": "system", "content": PARSE_PROMPT},
            {"role": "user", "content": query},
        ],
        temperature=0,
    )
    raw = completion.choices[0].message.content
    return extract_json(raw)


# 코스를 만들려면 반드시 있어야 하는 슬롯. 여기 없으면(=null) 예전처럼 "서울"이나
# 임의 카테고리로 추론해서 채우지 않고, 사용자에게 되물어서 직접 채우게 합니다.
REQUIRED_FIELD_QUESTIONS = {
    "anchor_text": "어느 지역에서 찾아드릴까요? (예: 성수동)",
    "category_keywords": "어떤 종류의 장소를 찾으세요? (예: 브런치, 카페, 갤러리, 데이트 코스)",
}


def missing_required_fields(parsed: dict) -> list[str]:
    """parse_free_query 결과에서 필수 슬롯 중 비어있는(null) 것들의 키 목록."""
    return [key for key in REQUIRED_FIELD_QUESTIONS if not parsed.get(key)]


def build_clarification_message(missing: list[str]) -> str:
    """부족한 슬롯에 대해 되물을 안내 문구 생성."""
    questions = "\n".join(f"- {REQUIRED_FIELD_QUESTIONS[key]}" for key in missing)
    return "코스를 추천해드리려면 몇 가지가 더 필요해요.\n" + questions
