import sys
from pathlib import Path

import os
from dotenv import load_dotenv

# exe(PyInstaller)로 묶였을 때는 .env가 압축 해제된 임시 폴더(sys._MEIPASS) 루트에
# 같이 들어있음. python-dotenv의 기본 탐색(find_dotenv)에 맡기지 않고 위치를
# 명시적으로 지정해서, frozen 여부와 무관하게 항상 같은 자리를 보게 함.
if getattr(sys, "frozen", False):
    _ENV_PATH = Path(sys._MEIPASS) / ".env"
else:
    _ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY", "")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")

UPSTAGE_BASE_URL = "https://api.upstage.ai/v1"

# 참고: 모델명은 Upstage Console(console.upstage.ai/api/chat) 문서에서
# 최신값을 다시 한번 확인하세요. 발표 시점 기준 solar-pro2 / solar-pro3 사용 가능.
SOLAR_MODEL = "solar-pro2"
