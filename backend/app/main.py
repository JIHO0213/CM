import sys
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import json
import traceback

from app.schemas import PlanRequest, ReplanRequest
from app.pipeline import run_pipeline_stream, replan_for_disruption
from app.services import document_ai, course_contract

app = FastAPI(title="Kakao CourseMate Demo API")

# 데모 웹페이지(별도 도메인/포트)에서 호출하므로 CORS 허용.
# "*"로 전체 허용해뒀기 때문에 로컬 개발 중인 프론트(예: Vite 기본 포트 5173)도
# 별도 설정 없이 그대로 통과됩니다. 배포 시에는 프론트 실제 도메인으로 좁히세요.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 주의: 여기에 @app.exception_handler(Exception)을 두면 안 됩니다.
# Starlette는 bare Exception 핸들러를 CORS 미들웨어 "바깥"(ServerErrorMiddleware)에
# 배치해서, 정작 에러가 났을 때 응답에 CORS 허용 헤더가 안 붙는 문제가 있습니다.
# (브라우저에는 500 에러가 "CORS 에러"로 보이는 원인이 이것입니다.)
# 그래서 각 엔드포인트 안에서 직접 try/except로 처리합니다 — 이러면 정상적으로
# CORS 미들웨어를 통과한 응답이 나갑니다.


class QueryRequest(BaseModel):
    query: str


class CourseReplanRequest(BaseModel):
    query: str                              # 원래 사용자가 입력했던 문장 (그대로 다시 보냄)
    disruption_reason: str                  # 예: "갑자기 비가 옴", "○○ 가게가 문을 닫았어요"
    exclude_place_name: str | None = None    # 문제가 된 특정 장소 (있으면 다음 후보로 자동 교체)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/courses")
async def get_courses(req: QueryRequest):
    """
    프론트 계약용 엔드포인트. { "query": "자유 문장" } 하나만 받아서
    { "title", "courses": [...] } 형태로 반환. (내부에서 지역/카테고리/필수조건을
    자동으로 뽑아내고, 리뷰·영업여부·거리를 반영해 코스 3개를 구성합니다.)
    """
    try:
        return await course_contract.handle_free_query(req.query)
    except Exception:
        traceback.print_exc()  # 터미널에 실제 원인(Traceback)을 그대로 출력
        return JSONResponse(
            status_code=500,
            content={"error": "코스를 생성하는 중 문제가 발생했습니다."},
        )


@app.post("/api/courses/stream")
async def get_courses_stream(req: QueryRequest):
    """
    /api/courses와 같은 결과를 SSE로 스트리밍. Planner/Local-Expert/Critic/최종 설명
    각 단계가 "실제로" 시작될 때마다 { step, label } 이벤트를 보내고, 끝나면 { title,
    courses } (또는 결과 없음/에러) 를 result 이벤트로 보냄.
    프론트 로딩 UI가 고정 타이머가 아니라 실제 백엔드 처리 속도에 맞춰 갱신되도록 하기 위함.

    스트림이 이미 200으로 시작된 뒤에는 HTTP 상태 코드를 바꿀 수 없어서, 에러도 여기서
    "result" 이벤트 안에 error 필드로 담아 보냅니다(위 /api/courses처럼 500을 반환할 수 없음).
    """
    async def event_stream():
        try:
            async for chunk in course_contract.handle_free_query_stream(req.query):
                yield chunk
        except Exception:
            traceback.print_exc()
            yield {
                "event": "result",
                "data": json.dumps({"error": "코스를 생성하는 중 문제가 발생했습니다."}, ensure_ascii=False),
            }

    return EventSourceResponse(event_stream())


@app.post("/api/courses/replan")
async def replan_courses(req: CourseReplanRequest):
    """
    돌발 상황(비, 임시휴무 등) 입력 시 코스를 다시 계산.
    프론트의 '돌발 상황 발생! 코스 변경' 버튼이 이 엔드포인트를 호출합니다.
    /api/courses와 동일한 응답 모양({title, courses})에 disruption_reason만 추가로 담아 반환합니다.
    """
    try:
        return await course_contract.handle_replan(
            req.query, req.disruption_reason, req.exclude_place_name
        )
    except Exception:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": "코스를 재구성하는 중 문제가 발생했습니다."},
        )


@app.post("/api/parse-image")
async def parse_image(file: UploadFile = File(...)):
    """
    STEP2. SNS 캡처 이미지 업로드 → Document Parse → 장소 카드 JSON(좌표 포함).
    프론트의 'Scrap & Plan' 업로드 버튼이 이 엔드포인트를 호출합니다.

    반환된 {name, lat, lng, address}를 그대로
    /api/plan-courses 요청의 must_include_place 필드에 넣어서 보내면,
    사진에서 인식한 장소가 실제 코스의 정거장으로 반영됩니다.
    """
    try:
        content = await file.read()
        return await document_ai.parse_captured_image(content, file.filename)
    except Exception:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "이미지를 처리하는 중 문제가 발생했습니다."})


@app.post("/api/replan")
async def replan(req: ReplanRequest):
    """
    돌발 상황(비, 임시휴무 등) 입력 시 코스를 다시 계산.
    프론트의 '[돌발 상황 발생! 코스 변경]' 버튼이 이 엔드포인트를 호출합니다.
    """
    try:
        return await replan_for_disruption(req)
    except Exception:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "코스를 재구성하는 중 문제가 발생했습니다."})


@app.post("/api/plan-courses/stream")
async def plan_courses_stream(req: PlanRequest):
    """
    전체 파이프라인(STEP1~5)을 SSE로 스트리밍.
    프론트는 EventSource로 연결해 단계별 진행상황과 최종 코스 결과를 받습니다.
    """
    return EventSourceResponse(run_pipeline_stream(req))


@app.post("/api/plan-courses")
async def plan_courses_sync(req: PlanRequest):
    """
    스트리밍이 필요 없는 경우를 위한 단순 동기 버전(최종 결과만 반환).
    """
    try:
        result = None
        async for event in run_pipeline_stream(req):
            if event.startswith("event: result"):
                import json
                data_line = [l for l in event.splitlines() if l.startswith("data:")][0]
                result = json.loads(data_line[len("data:"):].strip())
        return result or {"courses": []}
    except Exception:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "코스를 생성하는 중 문제가 발생했습니다."})


def _resolve_frontend_dist() -> Path | None:
    """
    빌드된 프론트(CM-main/dist)를 찾아서 백엔드가 같은 포트로 같이 서빙할 수 있게 함
    (exe 배포판처럼 프론트/백엔드를 한 프로세스·한 포트로 묶을 때 씀).
    - PyInstaller로 묶인 exe로 실행 중이면: 압축 해제된 임시 폴더(sys._MEIPASS) 안의 dist/
    - 평소 `uvicorn app.main:app`으로 개발 중이면: 이 저장소의 ../CM-main/dist
    둘 다 없으면(프론트를 아직 빌드 안 한 개발 초기 상태) None → API 서버만 동작.
    """
    if getattr(sys, "frozen", False):
        candidate = Path(sys._MEIPASS) / "dist"
    else:
        candidate = Path(__file__).resolve().parent.parent.parent / "CM-main" / "dist"
    return candidate if candidate.exists() else None


_frontend_dist = _resolve_frontend_dist()
if _frontend_dist:
    # 반드시 다른 라우트들을 다 등록한 "다음"에 마운트해야 함 — StaticFiles("/")가
    # 먼저 등록되면 /api/... 요청까지 이 정적 파일 서빙이 가로채 버림(경로 매칭이
    # 등록 순서대로 처리되기 때문).
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
