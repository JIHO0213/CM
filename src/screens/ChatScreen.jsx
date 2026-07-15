import { useCallback, useEffect, useRef, useState } from 'react'
import AppHeader from '../components/AppHeader'
import ChatAiMessage from '../components/ChatAiMessage'

// 자유 입력은 별도 매칭 로직이 없어서 항상 이 caseId를 기본값으로 사용
// (칩을 누르면 아래 SUGGESTION_CHIPS가 각자 정확한 caseId를 직접 넘겨줌)
const DEFAULT_CASE_ID = 'case1'

// 입력창 아래 추천 칩 3개: 클릭하면 해당 프롬프트가 바로 전송됨
const SUGGESTION_CHIPS = [
  {
    caseId: 'case1',
    label: '유모차+반려동물',
    prompt: '성수동에서 유모차 진입 가능하고 반려동물 동반되는 브런치 코스',
  },
  {
    caseId: 'case2',
    label: '비오는날+채식',
    prompt: '비 오는 날 채식 메뉴 있고 동선 안 꼬이는 강남 데이트 코스, 예산 10만원',
  },
  {
    caseId: 'case3',
    label: '웨이팅회피+가성비',
    prompt: '제주 여행 중 웨이팅 없고 가성비 좋은 3끼 맛집 코스, 인원 4명',
  },
]

const STORAGE_KEY = 'coursemate_chat_history' // localStorage에 채팅 내역을 저장할 때 쓰는 키

// localStorage에서 이전 채팅 내역을 불러옴 (저장된 게 없거나 깨졌으면 빈 배열)
function loadStoredMessages() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export default function ChatScreen() {
  const [messages, setMessages] = useState(loadStoredMessages) // 채팅 내역 (새로고침해도 유지됨)
  const [input, setInput] = useState('') // 입력창에 타이핑 중인 값
  // 메시지마다 고유 id를 매기기 위한 카운터. 저장된 내역이 있으면 그다음 번호부터 이어감
  const nextId = useRef(messages.reduce((max, m) => Math.max(max, m.id), -1) + 1)
  const listRef = useRef(null) // 채팅 내역 스크롤 영역(고정 높이, 이 안에서 스크롤됨)

  const hasStarted = messages.length > 0 // 아직 대화 전이면 중앙 화면, 시작했으면 채팅 화면

  // 채팅 내역이 바뀔 때마다 localStorage에 저장 (새로고침해도 대화가 남아있게)
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
  }, [messages])

  // 스크롤 영역을 맨 아래로 이동시키는 함수 (참조가 안 바뀌도록 useCallback으로 고정)
  const scrollToBottom = useCallback(() => {
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [])

  // 새 메시지가 추가될 때마다 맨 아래로 스크롤
  // (STEP 로딩·결과 카드로 내용이 더 늘어나는 건 ChatAiMessage가 onGrow로 알려줌)
  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // 유저 메시지 + AI 메시지(로딩부터 시작)를 함께 채팅 내역에 추가
  const sendMessage = (text, caseId) => {
    const trimmed = text.trim()
    if (!trimmed) return
    setMessages((prev) => [
      ...prev,
      { id: nextId.current++, role: 'user', text: trimmed },
      { id: nextId.current++, role: 'ai', caseId },
    ])
    setInput('')
  }

  // 입력창에서 직접 제출했을 때: 기본 caseId(case1) 사용
  const handleSubmit = (e) => {
    e.preventDefault()
    sendMessage(input, DEFAULT_CASE_ID)
  }

  // 추천 칩 클릭 시: 칩이 가진 프롬프트+caseId로 바로 전송 (엔터 불필요)
  const handleChipClick = (chip) => {
    sendMessage(chip.prompt, chip.caseId)
  }

  // AI 메시지의 결과 로딩이 끝나면 해당 메시지에 결과를 저장 (새로고침 복원용)
  const handleAiComplete = (msgId, course) => {
    setMessages((prev) => prev.map((m) => (m.id === msgId ? { ...m, course } : m)))
  }

  // "처음으로" 버튼: 현재 대화를 지우고 초기 화면으로 돌아감
  const handleReset = () => {
    setMessages([])
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

  // 추천 칩 목록 (입력창 바로 아래에 표시)
  const suggestionChips = (
    <div className="mt-3 flex flex-wrap justify-center gap-2">
      {SUGGESTION_CHIPS.map((chip) => (
        <button
          key={chip.caseId}
          type="button"
          onClick={() => handleChipClick(chip)}
          className="rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:border-[#FEE500] hover:bg-[#FEE500]/10"
        >
          {chip.label}
        </button>
      ))}
    </div>
  )

  return (
    <div className="mx-auto flex h-screen max-w-lg flex-col px-4">
      {!hasStarted ? (
        // 대화 시작 전: 화면 정중앙에 배지 + 타이틀 + 입력창 + 추천 칩
        <div className="flex flex-1 flex-col items-center justify-center">
          <AppHeader title="어디로 갈까요?" subtitle="궁금한 코스를 자유롭게 물어보세요" />
          {inputForm}
          {suggestionChips}
        </div>
      ) : (
        // 대화 시작 후: 채팅 내역이 위에 쌓이고, 입력창은 항상 하단에 고정
        <>
          {/* 상단 바: 배지 + 처음으로(대화 초기화) 버튼 */}
          <div className="flex items-center justify-between border-b border-gray-200 py-3">
            <span className="rounded-full bg-[#FEE500] px-3 py-1 text-xs font-bold text-gray-900">
              카카오 코스메이트
            </span>
            <button
              type="button"
              onClick={handleReset}
              className="text-xs font-medium text-gray-500 hover:text-gray-900"
            >
              처음으로
            </button>
          </div>

          <div ref={listRef} className="flex-1 space-y-4 overflow-y-auto py-6">
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
                    <ChatAiMessage
                      caseId={msg.caseId}
                      initialCourse={msg.course}
                      onGrow={scrollToBottom}
                      onComplete={(course) => handleAiComplete(msg.id, course)}
                    />
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
