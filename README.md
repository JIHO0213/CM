# 카카오 코스메이트 (프론트엔드 데모)

로컬 코스 추천 서비스의 프론트엔드 데모입니다.

## 실행 방법

```bash
# 1. 의존성 설치 (최초 1회)
npm install

# 2. 카카오맵 API 키 설정 (최초 1회)
cp .env.example .env
# .env 파일을 열어서 VITE_KAKAO_MAP_KEY 값을 발급받은 키로 교체

# 3. 개발 서버 실행
npm run dev
```

브라우저에서 `http://localhost:5173` 으로 접속하세요.

## 폴더 구조

```
src/
├── api.js              # API 호출 함수 (USE_MOCK 스위치)
├── mock/               # mock JSON 데이터
│   ├── case1.json
│   ├── case2.json
│   └── case3.json
├── lib/                 # 화면과 무관한 유틸/설정
│   ├── kakaoMapLoader.js # 카카오맵 SDK 스크립트 로더
│   └── courseColors.js   # 코스별 색상(A=파랑/B=초록/C=주황)
├── components/         # 재사용 가능한 UI 조각
│   ├── AppHeader.jsx
│   ├── ChatAiMessage.jsx  # AI 말풍선 (STEP 로딩 → 결과 카드 전환)
│   ├── CourseCard.jsx
│   ├── MapView.jsx        # 카카오맵 실연동 (마커+경로선+강조)
│   └── ReasoningStep.jsx
├── screens/            # 화면 단위 컴포넌트
│   └── ChatScreen.jsx  # 채팅형 UI 화면 (하나로 통합)
├── App.jsx             # 앱 진입 컴포넌트 (라우팅 없이 ChatScreen 렌더링)
├── main.jsx            # React 앱 진입점
└── index.css           # Tailwind CSS
```

## 기술 스택

- React + Vite
- Tailwind CSS
- 상태관리: useState (Redux 미사용)
