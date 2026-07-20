"""
더블클릭 한 번으로 백엔드(API)+프론트(빌드된 정적 파일)를 같은 포트로 같이 띄우는
exe 진입점. 개발 중엔 안 씀(그냥 `uvicorn app.main:app`으로 실행) — 이건 대회 당일
같은 공용 노트북에서 설치 없이 바로 실행하기 위한 배포용 진입점.

PyInstaller로 이 파일을 --onefile로 묶으면 CourseMate.exe 하나가 나옴:
  pyinstaller --onefile --name CourseMate ^
    --add-data "..\CM-main\dist;dist" ^
    --add-data "app\data;app\data" ^
    --add-data ".env;." ^
    run_desktop.py
"""
import threading
import time
import urllib.request
import webbrowser

import uvicorn

from app.main import app

HOST = "127.0.0.1"
PORT = 8000


def _open_browser_when_ready() -> None:
    url = f"http://{HOST}:{PORT}"
    for _ in range(60):  # 최대 약 30초 대기
        try:
            urllib.request.urlopen(f"{url}/health", timeout=1)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(0.5)
    print("[안내] 서버가 30초 안에 뜨지 않았어요. 위쪽 에러 메시지를 확인해주세요.")


def main() -> None:
    print("=" * 56)
    print(" 카카오 코스메이트 데모 서버를 시작합니다...")
    print(f" 잠시 후 브라우저가 자동으로 열립니다: http://{HOST}:{PORT}")
    print(" 종료하려면 이 창을 닫으면 됩니다.")
    print("=" * 56)

    threading.Thread(target=_open_browser_when_ready, daemon=True).start()
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
