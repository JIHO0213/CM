"""
영업 상황·시간대 반영.

중요: 카카오 로컬 API는 영업시간/실시간 영업여부를 제공하지 않습니다
(상호명·주소·좌표·카테고리·전화번호까지만 제공). 그래서 리뷰와 동일한 패턴으로
app/data/opening_hours.json 에 미리 준비한 영업시간 데이터를 기준으로,
"지금(요청 시각) 영업 중인지"를 서버가 직접 계산합니다.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

OPENING_HOURS_PATH = Path(__file__).resolve().parent.parent / "data" / "opening_hours.json"

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


def _load_opening_hours() -> dict:
    if not OPENING_HOURS_PATH.exists():
        return {}
    with open(OPENING_HOURS_PATH, encoding="utf-8") as f:
        return json.load(f)


def format_hours_text(place_name: str) -> str:
    """프론트에 보여줄 'hours' 필드용 사람이 읽는 문자열."""
    hours = _load_opening_hours().get(place_name)
    if not hours:
        return "영업시간 정보 없음"
    if hours.get("closed_days"):
        days = ", ".join(hours["closed_days"])
        return f"{days} 휴무, {hours['open']}-{hours['close']}"
    return f"매일 {hours['open']}-{hours['close']}"


def is_open_now(place_name: str, at: Optional[datetime] = None) -> dict:
    """
    데이터가 없는 장소는 '정보 없음'으로 처리(= 영업 중이라고 함부로 단정하지 않음).
    """
    at = at or datetime.now()
    hours = _load_opening_hours().get(place_name)
    if not hours:
        return {"status": "unknown", "note": "영업시간 정보가 없어 확인이 필요합니다."}

    today = WEEKDAY_KR[at.weekday()]
    if today in hours.get("closed_days", []):
        return {"status": "closed", "note": f"오늘({today}요일)은 정기 휴무일입니다."}

    now_min = at.hour * 60 + at.minute
    open_h, open_m = map(int, hours["open"].split(":"))
    close_h, close_m = map(int, hours["close"].split(":"))
    open_min, close_min = open_h * 60 + open_m, close_h * 60 + close_m

    if open_min <= now_min <= close_min:
        return {"status": "open", "note": f"{hours['open']}~{hours['close']} 영업 중입니다."}
    return {"status": "closed", "note": f"영업시간({hours['open']}~{hours['close']}) 외 시간입니다."}
