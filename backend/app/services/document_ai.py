"""
STEP 1~2. 입력 분석 레이어.
- parse_text_constraints: 자유 프롬프트(텍스트) → 제약조건 슬롯(JSON)으로 변환
  (기획안 STEP3 '제약조건 해석'에 해당, Solar Chat에게 JSON만 출력하도록 지시)
- parse_captured_image: SNS 캡처 이미지 → 장소 카드(JSON)
  (기획안 STEP2 'Upstage Document AI', Document Parse 사용)
"""
import tempfile

from openai import OpenAI
from langchain_upstage import UpstageDocumentParseLoader

from app.config import UPSTAGE_API_KEY, UPSTAGE_BASE_URL, SOLAR_MODEL
from app.services import kakao, reviews
from app.services.json_utils import extract_json

client = OpenAI(api_key=UPSTAGE_API_KEY, base_url=UPSTAGE_BASE_URL)

CONSTRAINT_SYSTEM_PROMPT = """당신은 사용자의 자연어 요청에서 코스 추천에 필요한
제약조건을 뽑아내는 파서입니다. 반드시 아래 JSON 스키마로만 답하세요. (마지막 항목 뒤에 쉼표를 붙이지 마세요)
설명이나 다른 텍스트를 절대 덧붙이지 마세요.

{
  "budget_krw": number | null,
  "headcount": number | null,
  "transport": "walk" | "public_transit" | "car" | null,
  "weather_sensitive": boolean,
  "mood_keywords": string[],
  "must_include": string[]
}
"""


def parse_text_constraints(user_prompt: str) -> dict:
    completion = client.chat.completions.create(
        model=SOLAR_MODEL,
        messages=[
            {"role": "system", "content": CONSTRAINT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )
    raw = completion.choices[0].message.content
    return extract_json(raw)


async def parse_captured_image(image_bytes: bytes, filename: str) -> dict:
    """
    업로드된 SNS 캡처 이미지를 Document Parse로 레이아웃 분석 → 텍스트 추출 →
    Solar Chat으로 장소명/주소 등 구조화 JSON 변환 → 주소를 좌표로 변환까지 한번에 처리.

    추가로, 뽑아낸 상호명이 우리 가게 데이터(리뷰/영업시간이 준비된 큐레이션 목록)에
    실제로 있는 곳인지 확인해서 is_known_store로 표시합니다. 코스 생성 파이프라인
    (agents.plan_courses)도 같은 목록으로 한 번 더 걸러내므로, 가게 데이터에 없는
    이미지는 최종적으로 코스에 반영되지 않습니다.
    """
    with tempfile.NamedTemporaryFile(suffix="_" + filename, delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    loader = UpstageDocumentParseLoader(tmp_path)
    docs = loader.load()
    extracted_text = "\n".join(d.page_content for d in docs)

    completion = client.chat.completions.create(
        model=SOLAR_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "다음은 SNS 캡처 이미지에서 추출한 텍스트입니다. "
                    '상호명, 주소, 특징을 {"name":..,"address":..,"notes":..} '
                    "형태의 JSON으로만 답하세요. 정보가 없으면 null."
                ),
            },
            {"role": "user", "content": extracted_text},
        ],
        temperature=0,
    )
    raw = completion.choices[0].message.content
    place = extract_json(raw)

    if place.get("address"):
        coords = await kakao.geocode_address(place["address"])
        if coords:
            place["lat"] = coords["lat"]
            place["lng"] = coords["lng"]
        else:
            place["lat"] = None
            place["lng"] = None
    else:
        place["lat"] = None
        place["lng"] = None

    known_names = reviews.known_place_names()
    resolved_name = place.get("name") if place.get("name") in known_names else None

    # OCR/LLM이 뽑아낸 상호명 표기가 카카오 공식 표기와 정확히 일치하지 않을 수 있어서,
    # 좌표를 구했다면 그 주변에서 같은 이름으로 한 번 더 검색해 가게 데이터와 대조해봄.
    if not resolved_name and place.get("name") and place.get("lat") is not None:
        candidates = await kakao.search_places(place["name"], place["lng"], place["lat"], radius=300)
        for c in candidates:
            if c["name"] in known_names:
                resolved_name = c["name"]
                break

    place["is_known_store"] = resolved_name is not None
    if resolved_name:
        place["name"] = resolved_name
    return place
