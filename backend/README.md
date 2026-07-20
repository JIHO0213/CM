# Kakao CourseMate — 데모 백엔드 스켈레톤

기획안 STEP1~STEP5 파이프라인(입력 분석 → Planner/Local-Expert/Critic → 환각 검증)을
FastAPI로 구현한 시작 코드입니다. 실제 API 키만 넣으면 바로 동작하는 구조로 짜여 있어요.

## 폴더 구조
```
backend/
├── app/
│   ├── main.py              # FastAPI 엔드포인트
│   ├── pipeline.py          # STEP1~5 전체 흐름 + SSE 스트리밍
│   ├── config.py            # 환경변수 로딩
│   ├── schemas.py           # 요청/응답 모델
│   └── services/
│       ├── document_ai.py   # Document Parse + 텍스트 제약조건 파싱
│       ├── agents.py        # Planner/Local-Expert/Critic 오케스트레이션
│       ├── kakao.py         # 카카오 로컬 검색 API + 길찾기
│       └── groundedness.py  # Groundedness Check
├── requirements.txt
└── .env.example
```

## 실행 방법
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env 열어서 UPSTAGE_API_KEY, KAKAO_REST_API_KEY 채우기

uvicorn app.main:app --reload --port 8000
```

브라우저에서 `http://localhost:8000/health` 접속해 `{"status":"ok"}` 뜨면 정상.

## API 키 발급
- **Upstage**: https://console.upstage.ai → API Keys 메뉴에서 발급 (Solar Chat, Document Parse, Groundedness Check 모두 동일 키 사용)
- **카카오**: https://developers.kakao.com → 애플리케이션 생성 → REST API 키 확인
  - 로컬 API(장소 검색)는 즉시 사용 가능
  - **길찾기 API(카카오모빌리티)는 별도 이용 신청이 필요**합니다. 신청 전에는 `kakao.py`의
    `get_route()`가 자동으로 직선거리 기반 근사치로 대체하니, 신청이 늦어져도 데모 진행에는 문제 없습니다.

## 데모 프론트에서 호출하는 방법

**1) 코스 생성 (스트리밍, 단계별 인디케이터 표시용)**
```javascript
const evtSource = new EventSource(); // GET은 EventSource 기본 지원이지만
// POST + SSE가 필요하므로 fetch + ReadableStream 사용을 권장합니다:

const res = await fetch("http://localhost:8000/api/plan-courses/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    prompt: "홍대에서 기념일 데이트, 조용한 파스타집 위주로",
    anchor: { name: "산울림1992", lat: 37.5519, lng: 126.9228 },
    budget: 100000,
    headcount: 2,
    transport: "walk",
    weather_sensitive: true
  })
});

const reader = res.body.getReader();
const decoder = new TextDecoder();
let buffer = "";
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  // "event: step\ndata: {...}\n\n" 단위로 파싱해서
  // 화면의 STEP1~4 인디케이터를 갱신하고,
  // "event: result" 가 오면 지도에 코스 A/B/C를 그리면 됩니다.
}
```

**2) 간단 버전 (스트리밍 없이 결과만)**
```javascript
const res = await fetch("http://localhost:8000/api/plan-courses", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ /* 위와 동일 */ })
});
const { courses } = await res.json();
```

**3) SNS 캡처 이미지 업로드 (Scrap & Plan)**
```javascript
const formData = new FormData();
formData.append("file", imageFile);
const res = await fetch("http://localhost:8000/api/parse-image", {
  method: "POST",
  body: formData,
});
const placeCard = await res.json(); // {name, address, notes}
```

## 리뷰 기반 장소 선정 (app/services/reviews.py + app/data/reviews.json)

카카오는 리뷰 텍스트를 주는 공식 API가 없어서(로컬 API는 상호명·주소·좌표까지만 제공),
`fetch_live_reviews()`가 항상 `None`을 반환하고 자동으로 `app/data/reviews.json`에
미리 써둔 리뷰로 대체되는 구조입니다.

리뷰 내용은 코드가 아니라 **`app/data/reviews.json` 파일 하나만 열어서** 수정하면
됩니다 (메모장, VS Code 어디서든 편집 가능). 형식:
```json
{
  "장소 이름(카카오맵 상호명과 동일하게)": [
    { "text": "리뷰 원문", "rating": 5 }
  ]
}
```

Local-Expert 단계에서 카카오 검색 결과 후보들 중, `mood_keywords`(예: "조용한", "감성",
"가성비")가 리뷰 문장에 얼마나 등장하는지로 점수를 매겨 가장 잘 맞는 곳을 고릅니다.
선택된 장소의 `matched_review` 필드에 근거가 된 리뷰 원문이 그대로 담겨 반환되므로,
프론트에서 "이 리뷰를 보고 추천했어요" 같은 카드로 바로 띄울 수 있습니다.

나중에 정식 리뷰 데이터(제휴 API 등)가 생기면 `fetch_live_reviews()` 함수 하나만
채워 넣으면 되고, 나머지 매칭/선정 로직은 그대로 재사용됩니다.

## 신규 구현 기능 (요청사항 반영)

### 영업 상황·시간대 반영 (app/services/hours.py + app/data/opening_hours.json)
카카오는 영업시간/실시간 영업여부 API도 제공하지 않습니다. 그래서 리뷰와 동일한 방식으로
`app/data/opening_hours.json`에 미리 준비한 영업시간 데이터를 기준으로, 요청 시각에
영업 중인지 서버가 직접 계산합니다. Local-Expert가 리뷰 순위대로 후보를 보다가 "영업 중"
또는 "정보 없음"인 첫 후보를 채택하고, 전부 닫혀 있으면 1순위를 그대로 쓰되
`may_be_closed: true`로 표시합니다.

### 사진 입력 반영 (app/services/document_ai.py + kakao.geocode_address)
`/api/parse-image`가 이제 상호명·주소뿐 아니라 **좌표(lat/lng)까지** 채워서 반환합니다
(주소 → 좌표 변환은 카카오 주소 검색 API 사용). 프론트에서 이 결과를
`/api/plan-courses`의 `must_include_place` 필드에 그대로 넣어 보내면, Planner가
모든 코스에 그 장소를 정거장으로 강제 포함시킵니다.

### 추천 이유 + 상황별 적합도 설명 (app/services/agents.py의 최종 설명 생성 단계)
기존에는 Planner가 실제 장소를 확정하기 *전*에 지어낸 이유를 그대로 썼습니다.
이제는 장소·리뷰·거리·영업상태가 다 확정된 *후*에 Solar에게 실제 데이터만 근거로
`reasoning`(추천 이유)과 `best_for`(어떤 상황에 적합한지)를 새로 생성하게 해서,
심사위원 질문에 실제 데이터로 답할 수 있게 했습니다.

### 돌발 상황 입력 → 코스 재구성 (`POST /api/replan`)
`ReplanRequest`(원래 요청 + 돌발 상황 설명 + 문제 장소명)를 보내면, 문제 장소를 제외하고
"비/눈"이 언급되면 실내 위주 조건을 강제로 켜서 코스를 다시 계산합니다.

### 카카오톡 공유 / 예약 / 카카오T 대체 (app/services/share.py)
- **카카오톡 공유**: 실제 전송은 프론트엔드의 카카오 JS SDK(`Kakao.Share.sendDefault`)가
  담당합니다. 백엔드는 각 코스 결과의 `share_payload` 필드에 그 SDK가 그대로 쓸 수 있는
  템플릿(제목/설명/링크)을 채워서 반환합니다.
- **카카오T**: 목적지를 자동으로 넘겨 호출하는 공식 API/딥링크가 공개되어 있지 않아
  지원하지 않습니다. 대신 각 코스의 `navi_deeplink` 필드에 **카카오맵 공식 길찾기
  딥링크**(`kakaomap://route?...`)를 담아, "동선을 앱으로 넘긴다"는 목적은 대체 구현했습니다.
- **가게 예약**: "카카오 예약"은 입점 사업자 전용 API라 접근할 수 없습니다. 대신 각 코스의
  `reservations` 필드에 전화 예약 링크(`tel:`)와 카카오맵 상세페이지 링크를 담았습니다.

## 프론트 계약 전용 엔드포인트 — `POST /api/courses`

프론트(coursemate2.vercel.app 등)가 채팅창에 입력한 문장 하나만 그대로 보내면 되는
간단한 계약입니다.

**요청**
```json
{ "query": "성수동에서 유모차 진입 가능하고 반려동물 동반되는 브런치 코스" }
```

**응답 (성공)**
```json
{
  "title": "성수동 브런치 코스",
  "courses": [
    {
      "id": 1,
      "title": "코스 성격",
      "description": "장소1 → 장소2 → 장소3",
      "duration": "약 2.5시간",
      "places": [
        {
          "name": "장소명",
          "lat": 37.5445,
          "lng": 127.0565,
          "hours": "매일 08:00-22:00",
          "verified": true,
          "matchedConstraints": ["유모차 진입 가능"],
          "reviewSnippet": "근거가 된 실제 리뷰 원문"
        }
      ]
    }
  ]
}
```

**응답 (조건에 맞는 코스를 못 찾았을 때)**
```json
{ "title": null, "courses": [], "message": "조건에 맞는 코스를 찾지 못했어요. 조건을 조금 완화해서 다시 시도해보세요." }
```

**응답 (서버 에러)** — HTTP 500
```json
{ "error": "코스를 생성하는 중 문제가 발생했습니다." }
```

**verified 판단 기준**: 근거가 된 리뷰가 실제로 있고(`matchedConstraints`/`reviewSnippet`이 채워짐),
영업 상태가 "닫힘"이 아닐 때만 `true`. 둘 중 하나라도 확신이 없으면 `false`로 보수적으로 처리합니다.

**동작 원리**: `query` 문장에서 Solar LLM이 지역명·카테고리·필수 요구사항 키워드를 뽑아내고
(`app/services/query_router.py`), 그 지역명을 좌표로 변환한 뒤(`kakao.geocode_district`)
그 좌표를 기준점 삼아 기존 파이프라인(Planner → Local-Expert → Critic → 최종 설명)을 그대로
재사용합니다. 코스 3개는 `asyncio.gather`로 동시에 처리해서 응답 시간을 줄였습니다.

**CORS**: 이미 전체 허용(`*`)이라 `http://localhost:5173`에서 오는 요청도 별도 설정 없이 통과됩니다.

**인증**: 없음(누구나 호출 가능). 데모 단계에서는 의도된 설정입니다.

## 지금 단계에서 임의로 단순화해둔 부분 (나중에 다듬을 곳)

- 영업시간/리뷰 데이터는 모두 목업(JSON 파일)입니다. 실제 데모 장소로 두 파일 다 채워 넣어야 해요.
- Critic이 위반을 발견해도 재설계 루프 없이 verdict만 표시합니다.
- 돌발 상황 재계산은 "전체 코스 다시 생성" 방식입니다. 지금 위치 기준으로 남은 구간만
  재계산하는 정교한 버전은 아직 없습니다.
- Critic이 위반을 발견해도 **현재는 Planner에게 되돌리지 않고 verdict만 표시**합니다 →
  실제 "재설계 루프"를 넣으려면 `agents.py`의 `plan_courses`에 verdict가 "ok"가 아닌 코스만
  Planner에 다시 보내는 재귀 호출을 추가하면 됩니다.
- 카카오 길찾기 미승인 시 자동으로 직선거리로 대체되므로, 발표 전 실제 승인이 나면
  `kakao.py`를 건드릴 필요 없이 그대로 실제 값으로 전환됩니다.

## 코드 검증용 시뮬레이션 스크립트 (`simulate.py`)

실제 업스테이지/카카오 API 키가 없어도, 이 스크립트로 전체 로직(파싱→코스생성→변환)이
제대로 동작하는지 확인할 수 있습니다. 외부 API 호출 부분만 가짜 응답으로 대체하고,
나머지는 실제 코드를 그대로 실행합니다.

```bash
cd backend
venv\Scripts\activate
python simulate.py
```

`/api/courses`, `/api/courses/replan` 요청을 실제로 흉내 내고, 응답 필드가 다 채워지는지,
에러 상황에서도 CORS가 정상인지까지 확인합니다. 코드를 수정한 뒤 "혹시 뭔가 깨지지
않았나" 싶을 때 이 스크립트를 돌려보면 실제 서버를 켜지 않고도 빠르게 확인할 수 있어요.

## 알려진 한계 (버그 아님)
- 리뷰 키워드 매칭은 "요청 키워드의 핵심 단어가 리뷰에 등장하는가"로 판단합니다.
  동의어(예: 요청 "반려동물" vs 리뷰 "강아지")까지는 못 잡습니다. 더 똑똑하게 하려면
  `reviews.explain_review_match()`처럼 Solar LLM 기반 매칭으로 바꿀 수 있습니다.
