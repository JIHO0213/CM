import { BrowserRouter, Routes, Route } from 'react-router-dom'
import InputScreen from './screens/InputScreen'
import ReasoningScreen from './screens/ReasoningScreen'
import ResultScreen from './screens/ResultScreen'

// 앱의 라우팅(화면 전환) 설정
export default function App() {
  return (
    // BrowserRouter: URL 경로에 따라 다른 화면을 보여줌
    <BrowserRouter>
      <Routes>
        {/* "/" 경로 → 입력 화면 */}
        <Route path="/" element={<InputScreen />} />
        {/* "/reasoning" 경로 → 추론(로딩) 화면 */}
        <Route path="/reasoning" element={<ReasoningScreen />} />
        {/* "/result" 경로 → 결과 화면 */}
        <Route path="/result" element={<ResultScreen />} />
      </Routes>
    </BrowserRouter>
  )
}
