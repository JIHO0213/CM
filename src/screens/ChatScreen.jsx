import { useRef, useState } from 'react'
import AppHeader from '../components/AppHeader'
import ChatAiMessage from '../components/ChatAiMessage'

// 입력 텍스트에 포함된 지역 키워드로 어떤 mock 케이스를 쓸지 결정
// 셋 다 안 걸리면 case1을 기본값으로 사용 (에러 방지)
function pickCaseId(text) {
  if (text.includes('홍대')) return 'case1'
  if (text.includes('강남')) return 'case2'
  if (text.includes('제주')) return 'case3'
  return 'case1'
}

export default function ChatScreen() {
  const [messages, setMessages] = useState([]) // 채팅 내역 (유저 메시지 + AI 메시지)
  const [input, setInput] = useState('') // 입력창에 타이핑 중인 값
  const nextId = useRef(0) // 메시지마다 고유 id를 매기기 위한 카운터

  const hasStarted = messages.length > 0 // 아직 대화 전이면 중앙 화면, 시작했으면 채팅 화면

  const handleSubmit = (e) => {
    e.preventDefault()
    const text = input.trim()
    if (!text) return // 빈 입력은 무시

    const caseId = pickCaseId(text)

    // 유저 메시지와, 로딩부터 시작하는 AI 메시지를 함께 추가
    setMessages((prev) => [
      ...prev,
      { id: nextId.current++, role: 'user', text },
      { id: nextId.current++, role: 'ai', caseId },
    ])
    setInput('')
  }

  // 입력창 (초기 화면 / 채팅 화면에서 공통으로 사용)
  const inputForm = (
    <form onSubmit={handleSubmit} className="flex w-full gap-2">
      <textarea
        rows={hasStarted ? 1 : 3}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="예: 성수동에서 브런치 먹고 갤러리 가고 싶어"
        className="flex-1 resize-none rounded-xl border border-gray-200 p-3 text-sm focus:border-[#FEE500] focus:outline-none"
      />
      <button
        type="submit"
        className="shrink-0 rounded-xl bg-[#FEE500] px-4 text-sm font-bold text-gray-900 transition hover:bg-[#f5d800]"
      >
        {hasStarted ? '전송' : '코스 추천 받기'}
      </button>
    </form>
  )

  return (
    <div className="mx-auto flex h-screen max-w-lg flex-col px-4">
      {!hasStarted ? (
        // 대화 시작 전: 화면 정중앙에 배지 + 타이틀 + 입력창만 표시
        <div className="flex flex-1 flex-col items-center justify-center">
          <AppHeader title="어디로 갈까요?" subtitle="궁금한 코스를 자유롭게 물어보세요" />
          {inputForm}
        </div>
      ) : (
        // 대화 시작 후: 채팅 내역이 위에 쌓이고, 입력창은 항상 하단에 고정
        <>
          <div className="flex-1 space-y-4 overflow-y-auto py-6">
            {messages.map((msg) =>
              msg.role === 'user' ? (
                // 유저 메시지: 오른쪽 정렬 말풍선
                <div key={msg.id} className="flex justify-end">
                  <div className="max-w-[80%] rounded-2xl bg-[#FEE500] px-4 py-2 text-sm text-gray-900">
                    {msg.text}
                  </div>
                </div>
              ) : (
                // AI 메시지: 왼쪽 정렬 말풍선 (내부에서 로딩→결과 전환)
                <div key={msg.id} className="flex justify-start">
                  <div className="w-[90%] rounded-2xl border border-gray-200 bg-white px-4 py-3">
                    <ChatAiMessage caseId={msg.caseId} />
                  </div>
                </div>
              )
            )}
          </div>

          {/* 하단 고정 입력창 */}
          <div className="border-t border-gray-200 bg-white py-3">{inputForm}</div>
        </>
      )}
    </div>
  )
}
