"""
리뷰 기반 장소 선정.

중요: 카카오 로컬 API는 리뷰 텍스트/평점을 제공하지 않습니다(상호명·주소·좌표·
카테고리·전화번호까지만 제공). 카카오맵 상세페이지 크롤링은 이용약관 위반 소지가
있고 페이지 구조 변경에 취약해 데모용으로 권장하지 않습니다.

그래서 구조는 "실시간 시도 → 실패 시 준비된 리뷰로 대체"로 짜두되,
fetch_live_reviews()는 현재 항상 None을 반환합니다. 나중에 정식 리뷰 데이터
소스(제휴 API 등)가 생기면 이 함수 하나만 구현해 넣으면 나머지 로직은
그대로 재사용됩니다.

리뷰 원본 데이터는 app/data/reviews.json 에 있습니다. 코드를 몰라도 그 파일만
열어서(메모장/VS Code 등) 장소 이름과 리뷰 문장을 채워 넣으면 됩니다.
"""
import json
from pathlib import Path
from typing import Optional

from openai import OpenAI

from app.config import UPSTAGE_API_KEY, UPSTAGE_BASE_URL, SOLAR_MODEL

client = OpenAI(api_key=UPSTAGE_API_KEY, base_url=UPSTAGE_BASE_URL)

REVIEWS_JSON_PATH = Path(__file__).resolve().parent.parent / "data" / "reviews.json"

DEFAULT_REVIEWS = [
    {"text": "무난하게 괜찮은 곳이에요.", "rating": 4},
]


def _load_mock_reviews() -> dict[str, list[dict]]:
    if not REVIEWS_JSON_PATH.exists():
        return {}
    with open(REVIEWS_JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def known_place_names() -> set[str]:
    """
    리뷰/영업시간 데이터가 실제로 준비된 장소 이름 목록.
    데모 특성상 "무난하게 괜찮은 곳이에요" 같은 기본값 대신 실제 리뷰가 있는 곳만
    코스에 노출시키고 싶을 때(agents.py의 Local-Expert 단계) 카카오 검색 결과를
    이 목록으로 걸러내는 데 씁니다.
    """
    return set(_load_mock_reviews().keys())


def fetch_live_reviews(place_name: str) -> Optional[list[dict]]:
    """
    실시간 리뷰 수집 시도 자리. 현재는 카카오 쪽에 공식 리뷰 API가 없어
    항상 None을 반환합니다. (제휴 데이터 등이 생기면 여기만 구현)
    """
    return None


def get_reviews_for_place(place_name: str) -> list[dict]:
    live = fetch_live_reviews(place_name)
    if live:
        return live
    mock_reviews = _load_mock_reviews()
    return mock_reviews.get(place_name, DEFAULT_REVIEWS)


def keyword_matches(keyword: str, text: str) -> bool:
    """
    키워드 전체 문구가 리뷰에 토씨 하나 안 틀리고 그대로 있어야만 매칭되던 문제를 완화.
    예: 요청 키워드 "유모차 진입 가능" / 리뷰 "유모차 끌고 들어가기 편했어요"
        → 기존(완전 일치)엔 매칭 실패, 지금(핵심 단어 일치)은 매칭 성공.
    키워드의 첫 단어(핵심 명사, 예: '유모차', '반려동물')가 리뷰 텍스트에 포함되면
    매칭된 것으로 봅니다. 완벽하진 않지만, 완전 일치보다 훨씬 실용적입니다.
    """
    if not keyword or not text:
        return False
    core = keyword.split()[0]
    return core in text


def _keyword_score(review_text: str, mood_keywords: list[str]) -> int:
    return sum(1 for kw in mood_keywords if keyword_matches(kw, review_text))


def rank_places(candidates: list[dict], mood_keywords: list[str]) -> list[dict]:
    """
    후보 전체를 리뷰 매칭 점수 순으로 정렬해서 반환.
    agents.py의 Local-Expert가 1순위부터 영업 여부를 확인하며 순서대로 채택합니다.
    """
    ranked = []
    for c in candidates:
        place_reviews = get_reviews_for_place(c["name"])
        best_review, best_score = None, -1
        for r in place_reviews:
            s = _keyword_score(r["text"], mood_keywords)
            if s > best_score:
                best_score, best_review = s, r
        entry = dict(c)
        entry["matched_review"] = best_review
        entry["review_match_score"] = best_score
        ranked.append(entry)
    ranked.sort(key=lambda x: x["review_match_score"], reverse=True)
    return ranked


def pick_best_place(candidates: list[dict], mood_keywords: list[str]) -> dict:
    """하위 호환용: rank_places의 1순위만 반환."""
    ranked = rank_places(candidates, mood_keywords)
    return ranked[0] if ranked else {}


def explain_review_match(place_name: str, matched_review: dict, mood_keywords: list[str]) -> str:
    """
    (선택) Solar LLM으로 '왜 이 리뷰 때문에 이 장소를 골랐는지' 한 줄 설명 생성.
    리뷰 원문 자체는 건드리지 않고, 설명만 새로 생성해 화면에 곁들일 수 있습니다.
    """
    if not matched_review:
        return f"{place_name}은(는) 참고할 리뷰가 없어 기본 후보로 선택되었습니다."

    prompt = (
        f"장소: {place_name}\n리뷰: \"{matched_review['text']}\"\n"
        f"찾는 분위기 키워드: {', '.join(mood_keywords) if mood_keywords else '(특별한 무드 조건 없음)'}\n"
        "위 리뷰가 이 무드 키워드와 왜 잘 맞는지 한 문장으로 설명해줘."
    )
    completion = client.chat.completions.create(
        model=SOLAR_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return completion.choices[0].message.content.strip()
