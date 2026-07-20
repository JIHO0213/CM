"""
카카오 API 연동 레이어.
- 장소 검색: 카카오 로컬 API (키워드 검색) — 무료, 즉시 사용 가능
- 주소/지역명 -> 좌표 변환: 카카오 주소 검색 API
- 길찾기(거리/시간): 카카오모빌리티 길찾기 API — 별도 이용 신청 필요.
  신청 전 데모 단계에서는 하버사인(직선거리) 기반 근사치로 대체하도록
  get_route()에 폴백 로직을 넣어뒀습니다.
- 딥링크: 카카오맵 공식 URL Scheme으로 동선을 앱에 넘기는 링크 생성
"""
import math
from typing import Optional

import httpx

from app.config import KAKAO_REST_API_KEY

LOCAL_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
ADDRESS_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/address.json"
DIRECTIONS_URL = "https://apis-navi.kakaomobility.com/v1/directions"

HEADERS = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}


async def search_places(query: str, lng: float, lat: float, radius: int = 1500) -> list[dict]:
    """
    Local-Expert Agent가 "홍대 조용한 파스타집" 같은 카테고리/무드를
    실제 장소 후보로 바꿀 때 사용.
    """
    params = {
        "query": query,
        "x": lng,
        "y": lat,
        "radius": radius,
        "sort": "accuracy",
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        res = await client.get(LOCAL_SEARCH_URL, headers=HEADERS, params=params)
        res.raise_for_status()
        data = res.json()

    return [
        {
            "name": doc["place_name"],
            "address": doc["road_address_name"] or doc["address_name"],
            "lat": float(doc["y"]),
            "lng": float(doc["x"]),
            "category": doc["category_name"],
            "phone": doc.get("phone", ""),
            "place_url": doc.get("place_url", ""),
        }
        for doc in data.get("documents", [])
    ]


async def geocode_address(address: str) -> Optional[dict]:
    """
    SNS 캡처 이미지에서 Document AI가 뽑아낸 '주소 텍스트'를 좌표로 변환.
    (사진 입력 → 지도 표시를 연결하는 핵심 다리 역할)
    """
    if not address:
        return None
    params = {"query": address}
    async with httpx.AsyncClient(timeout=5.0) as client:
        res = await client.get(ADDRESS_SEARCH_URL, headers=HEADERS, params=params)
        res.raise_for_status()
        data = res.json()
    docs = data.get("documents", [])
    if not docs:
        return None
    d = docs[0]
    return {"lat": float(d["y"]), "lng": float(d["x"]), "address": address}


async def geocode_district(name: str) -> Optional[dict]:
    """
    '성수동' 같은 동네/지역 이름을 좌표로 변환. 주소 검색 API로 먼저 시도하고,
    실패하면 키워드 검색(반경 제한 없이)으로 한번 더 시도.
    이렇게 얻은 좌표는 실제 '장소'가 아니라 코스 검색을 시작할 기준점(가상 앵커)입니다.
    """
    coords = await geocode_address(name)
    if coords:
        return coords

    async with httpx.AsyncClient(timeout=5.0) as client:
        res = await client.get(LOCAL_SEARCH_URL, headers=HEADERS, params={"query": name})
        res.raise_for_status()
        data = res.json()
    docs = data.get("documents", [])
    if not docs:
        return None
    d = docs[0]
    return {"lat": float(d["y"]), "lng": float(d["x"]), "address": name}


def build_navi_deeplink(places: list[dict], mode: str = "CAR") -> str:
    """
    카카오맵 공식 URL Scheme(kakaomap://route)으로 동선을 카카오맵 앱에 넘기는 딥링크 생성.
    참고: 카카오T는 목적지를 자동으로 넘기는 공식 딥링크/API가 공개되어 있지 않아
    지원하지 않습니다(대신 이 카카오맵 길찾기 딥링크로 대체).
    최대 경유지 5개(vp1~vp5)까지 지원.
    """
    if len(places) < 2:
        return ""
    by = {"CAR": "car", "WALK": "foot", "TRANSIT": "publictransit", "BIKE": "bicycle"}.get(mode, "car")
    sp = places[0]
    ep = places[-1]
    waypoints = places[1:-1][:5]
    parts = [f"sp={sp['lat']},{sp['lng']}", f"ep={ep['lat']},{ep['lng']}", f"by={by}"]
    for i, wp in enumerate(waypoints, start=1):
        parts.append(f"vp{i}={wp['lat']},{wp['lng']}")
    return "kakaomap://route?" + "&".join(parts)


def _haversine_m(lat1, lng1, lat2, lng2) -> float:
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def get_route(origin: dict, destination: dict) -> dict:
    """
    두 지점 간 실제 이동거리/시간. 카카오모빌리티 길찾기 API 이용 신청이
    완료되어 있으면 실제 값을, 아니면 직선거리 기반 근사치를 반환합니다.
    """
    try:
        params = {
            "origin": f"{origin['lng']},{origin['lat']}",
            "destination": f"{destination['lng']},{destination['lat']}",
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(DIRECTIONS_URL, headers=HEADERS, params=params)
            res.raise_for_status()
            data = res.json()
        summary = data["routes"][0]["summary"]
        return {
            "distance_m": summary["distance"],
            "duration_min": round(summary["duration"] / 60, 1),
            "source": "kakao_mobility",
        }
    except Exception:
        # 길찾기 API 미승인/실패 시 폴백
        dist = _haversine_m(origin["lat"], origin["lng"], destination["lat"], destination["lng"])
        walking_speed_m_per_min = 67  # 도보 약 4km/h
        return {
            "distance_m": round(dist, 1),
            "duration_min": round(dist / walking_speed_m_per_min, 1),
            "source": "haversine_fallback",
        }
