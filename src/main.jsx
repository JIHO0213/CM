import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// React 앱을 HTML의 #root 요소에 마운트(연결)
createRoot(document.getElementById('root')).render(
  // StrictMode: 개발 중 잠재적 문제를 감지해주는 React 래퍼
  <StrictMode>
    <App />
  </StrictMode>,
)
