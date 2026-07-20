from typing import Optional
from pydantic import BaseModel


class AnchorPlace(BaseModel):
    name: str
    lat: float
    lng: float


class MustIncludePlace(BaseModel):
    """SNS 캡처 이미지에서 파싱된 뒤 좌표까지 채워진 장소 (사진 반영용)"""
    name: str
    lat: float
    lng: float
    address: Optional[str] = None


class PlanRequest(BaseModel):
    """프론트에서 넘어오는 사용자 입력 (STEP1 이후 Document AI가 구조화한 결과)"""
    prompt: str                      # 자유 프롬프트 원문
    anchor: Optional[AnchorPlace] = None
    budget: Optional[int] = None     # 원 단위
    headcount: Optional[int] = None
    transport: Optional[str] = None  # 도보/대중교통/자차 등
    weather_sensitive: bool = False  # "비 오면 실내 위주" 같은 조건 유무
    mood_keywords: list[str] = []    # "조용한", "감성", "가성비" 등
    must_include_place: Optional[MustIncludePlace] = None  # 사진에서 인식된 장소


class ReplanRequest(BaseModel):
    """돌발 상황 발생 시 코스 재구성 요청"""
    original_plan_request: PlanRequest
    disruption_reason: str            # 예: "갑자기 비가 옴", "가게가 휴무였음"
    exclude_place_name: Optional[str] = None  # 문제가 된 특정 장소는 다음 재계산에서 제외


class CandidateCourse(BaseModel):
    course_id: str
    label: str            # "최단거리" / "감성 충만" / "가성비" 등
    places: list[dict]    # 순서대로 방문할 장소 리스트
    total_distance_m: float
    total_duration_min: float
    reasoning: str         # 왜 이렇게 짰는지 (심사위원 데모용으로도 유용)


class VerifiedCourse(CandidateCourse):
    grounded: bool
    groundedness_note: str
