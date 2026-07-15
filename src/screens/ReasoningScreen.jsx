import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import ReasoningStep from '../components/ReasoningStep'

// AI가 추론하는 5단계 텍스트 (정적 데이터)
const REASONING_STEPS = [
  '사용자 입력을 분석하고 있어요...',
  '주변 인기 장소를 검색하고 있어요...',
  '이동 거리와 소요 시간을 계산하고 있어요...',
  '최적의 동선을 조합하고 있어요...',
  '맞춤 코스를 완성했어요!',
]

export default function ReasoningScreen() {
  const navigate = useNavigate()

  // visibleCount: 현재까지 보여줄 단계 수 (0이면 아무것도 안 보임)
  const [visibleCount, setVisibleCount] = useState(0)

  // 컴포넌트가 마운트되면 0.8초마다 단계를 하나씩 표시
  useEffect(() => {
    const timers = REASONING_STEPS.map((_, index) =>
      setTimeout(() => {
        setVisibleCount(index + 1)
      }, (index + 1) * 800)
    )

    // 5단계가 모두 끝나면 1초 뒤 결과 화면으로 자동 이동
    const navigateTimer = setTimeout(() => {
      navigate('/result')
    }, REASONING_STEPS.length * 800 + 1000)

    // 컴포넌트가 사라질 때 타이머 정리 (메모리 누수 방지)
    return () => {
      timers.forEach(clearTimeout)
      clearTimeout(navigateTimer)
    }
  }, [navigate])

  return (
    <div className="mx-auto min-h-screen max-w-lg px-4 py-10">
      <AppHeader
        title="코스를 만들고 있어요"
        subtitle="잠시만 기다려주세요"
      />

      {/* 로딩 스피너 */}
      <div className="mb-8 flex justify-center">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-[#FEE500]" />
      </div>

      {/* STEP 1~5 순차 표시 영역 */}
      <section className="space-y-3">
        {REASONING_STEPS.map((text, index) => (
          <ReasoningStep
            key={index}
            stepNumber={index + 1}
            text={text}
            isVisible={index < visibleCount}
          />
        ))}
      </section>
    </div>
  )
}
