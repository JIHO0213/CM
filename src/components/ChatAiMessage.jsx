import { useEffect, useState } from 'react'
import ReasoningStep from './ReasoningStep'
import CourseCard from './CourseCard'
import MapPlaceholder from './MapPlaceholder'
import { getCourseRecommendation } from '../api'

// 기존 ReasoningScreen에서 쓰던 STEP 1~5 문구 (그대로 재사용)
const REASONING_STEPS = [
  '사용자 입력을 분석하고 있어요...',
  '주변 인기 장소를 검색하고 있어요...',
  '이동 거리와 소요 시간을 계산하고 있어요...',
  '최적의 동선을 조합하고 있어요...',
  '맞춤 코스를 완성했어요!',
]

// AI 말풍선 하나: 처음엔 STEP 로딩을 보여주다가, 끝나면 같은 말풍선 안에서
// 지도 + 코스 카드로 바뀌는 컴포넌트 (caseId는 어떤 mock 데이터를 쓸지 알려줌)
export default function ChatAiMessage({ caseId }) {
  const [visibleCount, setVisibleCount] = useState(0) // 지금까지 보여준 STEP 개수
  const [course, setCourse] = useState(null) // 로딩이 끝나면 여기에 결과 데이터가 들어옴

  useEffect(() => {
    // STEP 1~5를 0.8초 간격으로 순서대로 표시
    const stepTimers = REASONING_STEPS.map((_, index) =>
      setTimeout(() => setVisibleCount(index + 1), (index + 1) * 800)
    )

    // 모든 STEP이 끝난 뒤, mock 데이터를 불러와서 결과 화면으로 전환
    const loadTimer = setTimeout(() => {
      getCourseRecommendation(caseId).then(setCourse)
    }, REASONING_STEPS.length * 800 + 500)

    // 컴포넌트가 사라질 때 타이머 정리 (메모리 누수 방지)
    return () => {
      stepTimers.forEach(clearTimeout)
      clearTimeout(loadTimer)
    }
  }, [caseId])

  // 아직 결과가 안 왔으면 STEP 로딩 목록을 보여줌
  if (!course) {
    return (
      <div className="space-y-2">
        {REASONING_STEPS.map((text, index) => (
          <ReasoningStep
            key={index}
            stepNumber={index + 1}
            text={text}
            isVisible={index < visibleCount}
          />
        ))}
      </div>
    )
  }

  // 결과가 도착하면 지도 + 코스 카드들을 같은 말풍선 안에 표시
  return (
    <div className="space-y-4">
      <MapPlaceholder />
      {course.courses.map((c, index) => (
        <CourseCard
          key={c.id}
          index={index + 1}
          title={c.title}
          description={c.description}
          duration={c.duration}
          places={c.places}
        />
      ))}
    </div>
  )
}
