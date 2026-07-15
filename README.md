# 카카오 코스메이트 (프론트엔드 데모)

로컬 코스 추천 서비스의 프론트엔드 데모입니다.

## 실행 방법

```bash
# 1. 의존성 설치 (최초 1회)
npm install

# 2. 개발 서버 실행
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
├── components/         # 재사용 가능한 UI 조각
│   ├── AppHeader.jsx
│   ├── CourseCard.jsx
│   ├── MapPlaceholder.jsx
│   ├── PresetButton.jsx
│   └── ReasoningStep.jsx
├── screens/            # 화면 단위 컴포넌트
│   ├── InputScreen.jsx
│   ├── ReasoningScreen.jsx
│   └── ResultScreen.jsx
├── App.jsx             # 라우팅 설정
├── main.jsx            # React 앱 진입점
└── index.css           # Tailwind CSS
```

## 기술 스택

- React + Vite
- Tailwind CSS
- react-router-dom
- 상태관리: useState / useContext (Redux 미사용)
