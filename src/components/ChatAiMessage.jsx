import { useEffect, useState } from 'react'
import ReasoningStep from './ReasoningStep'
import CourseCard from './CourseCard'
import MapView from './MapView'
import { getCourseRecommendation } from '../api'
import { getCourseColor } from '../lib/courseColors'

// 기존 ReasoningScreen에서 쓰던 STEP 1~5 문구 (그대로 재사용)
const REASONING_STEPS = [
  '사용자 입력을 분석하고 있어요...',
  '주변 인기 장소를 검색하고 있어요...',
  '이동 거리와 소요 시간을 계산하고 있어요...',
  '최적의 동선을 조합하고 있어요...',
  '맞춤 코스를 완성했어요!',
]

// AI 말풍선 하나: 처음엔 STEP 로딩을 보여주다가, 끝나면 같은 말풍선 안에서
// 지도 + 코스 카드로 바뀌는 컴포넌트
// caseId: 어떤 mock 데이터를 쓸지
// initialCourse: 새로고침 등으로 이미 완료된 결과를 복원할 때 (있으면 로딩 애니메이션 없이 바로 결과 표시)
// onGrow: 내용이 늘어날 때마다 부모에게 알려줘서 자동 스크롤시킴
// onComplete: 결과 로딩이 끝나면 부모에게 결과를 전달 (localStorage 저장용)
export default function ChatAiMessage({ caseId, initialCourse, onGrow, onComplete }) {
  const [visibleCount, setVisibleCount] = useState(initialCourse ? REASONING_STEPS.length : 0)
  const [course, setCourse] = useState(initialCourse ?? null) // 로딩이 끝나면 여기에 결과 데이터가 들어옴
  const [activeIndex, setActiveIndex] = useState(null) // 마우스를 올리거나 클릭한 코스 (null이면 전체 표시)

  useEffect(() => {
    if (initialCourse) return // 이미 완료된 메시지를 복원하는 경우엔 애니메이션 다시 재생 안 함

    // STEP 1~5를 0.8초 간격으로 순서대로 표시
    const stepTimers = REASONING_STEPS.map((_, index) =>
      setTimeout(() => setVisibleCount(index + 1), (index + 1) * 800)
    )

    // 모든 STEP이 끝난 뒤, mock 데이터를 불러와서 결과 화면으로 전환
    const loadTimer = setTimeout(() => {
      getCourseRecommendation(caseId).then((data) => {
        setCourse(data)
        onComplete?.(data)
      })
    }, REASONING_STEPS.length * 800 + 500)

    // 컴포넌트가 사라질 때 타이머 정리 (메모리 누수 방지)
    return () => {
      stepTimers.forEach(clearTimeout)
      clearTimeout(loadTimer)
    }
  }, [caseId, initialCourse])

  // STEP이 하나씩 보이거나 결과가 도착해서 말풍선 높이가 바뀔 때마다 스크롤을 맨 아래로
  useEffect(() => {
    onGrow?.()
  }, [visibleCount, course, onGrow])

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
  // 카드에 마우스를 올리거나 클릭하면 activeIndex가 바뀌면서 지도에서 해당 코스만 강조됨
  return (
    <div className="space-y-4">
      <MapView courses={course.courses} activeIndex={activeIndex} />
      <div className="space-y-4">
        {course.courses.map((c, index) => (
          <CourseCard
            key={c.id}
            index={index + 1}
            title={c.title}
            description={c.description}
            duration={c.duration}
            places={c.places}
            color={getCourseColor(index)}
            isActive={activeIndex === index}
            onMouseEnter={() => setActiveIndex(index)}
            onMouseLeave={() => setActiveIndex(null)}
            onClick={() => setActiveIndex(index)}
          />
        ))}
      </div>
    </div>
  )
}
