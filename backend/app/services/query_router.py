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
  "category_keyword": "찾는 장소 종류 (예: '브런치', '카페'). 없으면 null",
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
