"""
카카오톡 공유, 예약, 카카오T 연동을 위한 데이터/링크 준비 레이어.

* 카카오톡 공유: 실제 전송은 프론트엔드의 카카오 JS SDK(Kakao.Share.sendDefault)가
  담당합니다. 백엔드는 그 SDK가 그대로 넣을 수 있는 템플릿 데이터만 만들어줍니다.
* 카카오T: 목적지를 자동으로 넘겨 호출하는 공식 API/딥링크가 없어 지원하지 않습니다.
  대신 카카오맵 길찾기 딥링크(kakao.build_navi_deeplink)로 "동선 전달" 목적을 대체합니다.
* 가게 예약: "카카오 예약"은 입점 사업자 전용이라 일반 API로 접근할 수 없습니다.
  대신 전화 예약(tel: 링크)과 카카오맵 상세페이지 링크(place_url)로 대체합니다.
"""


def build_share_payload(course: dict) -> dict:
    """
    프론트엔드가 Kakao.Share.sendDefault({...}) 호출 시 그대로 넣을 수 있는 형태.
    """
    place_names = " → ".join(p["name"] for p in course["places"])
    return {
        "object_type": "feed",
        "content": {
            "title": f"[{course['label']}] {place_names}",
            "description": course.get("reasoning", ""),
            "image_url": "",  # 발표 데모용 대표 이미지 URL로 채워 넣기
            "link": {"web_url": "", "mobile_web_url": ""},  # 배포된 데모 URL로 채워 넣기
        },
        "buttons": [
            {"title": "코스 자세히 보기", "link": {"web_url": "", "mobile_web_url": ""}}
        ],
    }


def build_reservation_info(place: dict) -> dict:
    """
    카카오 예약 API 접근 권한이 없으므로, 전화 예약 + 카카오맵 상세페이지 링크로 대체.
    """
    phone = place.get("phone") or ""
    return {
        "method": "call_or_web",
        "note": "카카오 예약은 입점 사업자만 접근 가능한 API라 직접 연동할 수 없어, 전화 예약과 카카오맵 페이지로 대체했습니다.",
        "tel_link": f"tel:{phone}" if phone else None,
        "kakaomap_place_url": place.get("place_url") or None,
    }
