import { useEffect, useState } from 'react'
import ReasoningStep from './ReasoningStep'
import CourseCard from './CourseCard'
import MapView from './MapView'
import { USE_MOCK, getCourseRecommendation, replanCourses, streamCourseRecommendation } from '../api'
import { getCourseColor } from '../lib/courseColors'

// 기존 ReasoningScreen에서 쓰던 STEP 1~5 문구 (그대로 재사용)
const REASONING_STEPS = [
  '사용자 입력을 분석하고 있어요...',
  '주변 인기 장소를 검색하고 있어요...',
  '이동 거리와 소요 시간을 계산하고 있어요...',
  '최적의 동선을 조합하고 있어요...',
  '맞춤 코스를 완성했어요!',
]

// 돌발 상황 버튼을 눌렀을 때 바로 고를 수 있는 예시 사유들 (직접 입력도 가능)
const DISRUPTION_PRESETS = ['갑자기 비가 와요', '장소가 문을 닫았어요', '웨이팅이 너무 길어요']

// AI 말풍선 하나: 처음엔 STEP 로딩을 보여주다가, 끝나면 같은 말풍선 안에서
// 지도 + 코스 카드로 바뀌는 컴포넌트
// caseId: mock 모드에서 어떤 mock 데이터를 쓸지 (USE_MOCK=false면 사용 안 함)
// query: 사용자가 입력한 실제 문장 (실제 백엔드 호출에 사용, 돌발 상황 재계산에도 재사용됨)
// mustIncludePlace: 첫 요청에서 SNS 캡처 이미지로 인식·검증된 장소({name,lat,lng,address}), 없으면 null
// initialCourse: 새로고침 등으로 이미 완료된 결과를 복원할 때 (있으면 로딩 애니메이션 없이 바로 결과 표시)
// onGrow: 내용이 늘어날 때마다 부모에게 알려줘서 자동 스크롤시킴
// onComplete: 결과 로딩이 끝나면 부모에게 결과를 전달 (localStorage 저장용)
export default function ChatAiMessage({ caseId, query, mustIncludePlace, initialCourse, onGrow, onComplete }) {
  // currentStep: 지금까지 시작된 가장 마지막 단계 번호 (1~5). 0이면 아직 아무 단계도 안 옴.
  // 실제 모드에선 백엔드가 SSE로 "이 단계 시작했어요" 신호를 보낼 때마다 갱신되므로,
  // 고정 타이머가 아니라 실제 처리 속도에 맞춰 올라감.
  const [currentStep, setCurrentStep] = useState(initialCourse ? REASONING_STEPS.length : 0)
  const [course, setCourse] = useState(initialCourse ?? null) // 로딩이 끝나면 여기에 결과 데이터가 들어옴
  const [error, setError] = useState(null) // 백엔드 호출이 실패했을 때 보여줄 메시지
  // 클릭하면 selectedIndex에 "고정"되고(다시 누르면 해제), 호버는 hoveredIndex로 임시 미리보기만 함.
  // 지도/카드에 실제로 강조할 코스는 "호버 중인 게 있으면 그걸 우선, 없으면 고정된 것" (null이면 전체 표시)
  const [selectedIndex, setSelectedIndex] = useState(null)
  const [hoveredIndex, setHoveredIndex] = useState(null)
  const activeIndex = hoveredIndex ?? selectedIndex

  // 돌발 상황 재계산 관련 상태
  const [showDisruptionForm, setShowDisruptionForm] = useState(false) // 사유 입력 폼 표시 여부
  const [disruptionReason, setDisruptionReason] = useState('') // 입력 중인 사유
  const [isReplanning, setIsReplanning] = useState(false) // 재계산 API 호출 중인지
  const [disruptionNote, setDisruptionNote] = useState(null) // 재계산 완료 후 보여줄 안내 문구

  useEffect(() => {
    if (initialCourse) return // 이미 완료된 메시지를 복원하는 경우엔 애니메이션 다시 재생 안 함

    let cancelled = false
    setCurrentStep(0)
    setError(null)

    // mock 모드는 실제 백엔드가 없어 진행 상황을 스트리밍할 수 없으므로, 예전처럼
    // 고정 타이머로 STEP 진행을 흉내냄 (USE_MOCK=false인 지금은 이 분기를 안 탐)
    if (USE_MOCK) {
      const stepTimers = REASONING_STEPS.map((_, index) =>
        setTimeout(() => {
          if (!cancelled) setCurrentStep((s) => Math.max(s, index + 1))
        }, (index + 1) * 800)
      )

      getCourseRecommendation({ query, caseId, mustIncludePlace })
        .then((data) => {
          if (cancelled) return
          stepTimers.forEach(clearTimeout)
          setCurrentStep(REASONING_STEPS.length)
          setCourse(data)
          onComplete?.(data)
        })
        .catch((err) => {
          if (cancelled) return
          stepTimers.forEach(clearTimeout)
          setError(err.message || '코스를 불러오지 못했어요')
        })

      return () => {
        cancelled = true
        stepTimers.forEach(clearTimeout)
      }
    }

    // 실제 모드: 백엔드가 SSE로 보내주는 "지금 이 단계 시작함" 신호를 그대로 STEP UI에 반영
    const controller = new AbortController()

    streamCourseRecommendation({
      query,
      mustIncludePlace,
      signal: controller.signal,
      onStep: (step) => {
        if (!cancelled) setCurrentStep(step)
      },
      onResult: (data) => {
        if (cancelled) return
        if (data?.error) {
          setError(data.error)
          return
        }
        setCurrentStep(REASONING_STEPS.length)
        setCourse(data)
        onComplete?.(data)
      },
    }).catch((err) => {
      if (cancelled || err.name === 'AbortError') return
      setError(err.message || '코스를 불러오지 못했어요')
    })

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [caseId, query, mustIncludePlace, initialCourse])

  // STEP이 하나씩 보이거나 결과/에러가 도착해서 말풍선 높이가 바뀔 때마다 스크롤을 맨 아래로
  useEffect(() => {
    onGrow?.()
  }, [currentStep, course, error, showDisruptionForm, isReplanning, disruptionNote, onGrow])

  // 돌발 상황 사유가 확정되면 재계산 API 호출
  const handleDisruptionSubmit = async (reason) => {
    const trimmed = reason.trim()
    if (!trimmed || isReplanning) return

    setIsReplanning(true)
    setShowDisruptionForm(false)
    try {
      const data = await replanCourses({ query, disruptionReason: trimmed })
      setCourse(data)
      setSelectedIndex(null)
      setHoveredIndex(null)
      setDisruptionNote('코스를 다시 추천했습니다.')
      onComplete?.(data)
    } catch (err) {
      setDisruptionNote(`코스 재계산에 실패했어요: ${err.message || '알 수 없는 오류'}`)
    } finally {
      setIsReplanning(false)
      setDisruptionReason('')
    }
  }

  // 백엔드 호출 자체가 실패한 경우 (서버 다운, 네트워크 오류 등)
  if (error) {
    return (
      <div className="space-y-1 text-sm text-red-600">
        <p>😥 {error}</p>
        <p className="text-xs text-gray-400">잠시 후 다시 시도해주세요.</p>
      </div>
    )
  }

  // 아직 결과가 안 왔으면 STEP 로딩 목록을 보여줌
  if (!course) {
    return (
      <div className="space-y-2">
        {REASONING_STEPS.map((text, index) => {
          const stepNumber = index + 1
          const status =
            stepNumber < currentStep ? 'done' : stepNumber === currentStep ? 'running' : 'pending'
          return <ReasoningStep key={index} stepNumber={stepNumber} text={text} status={status} />
        })}
      </div>
    )
  }

  // 응답은 왔지만 조건에 맞는 코스가 없는 경우: { title: null, courses: [], message: "..." }
  // needsClarification이면 지역/카테고리 같은 필수 정보가 부족해서 되묻는 중인 상태
  // (임의로 "서울" 등을 추론해서 채우지 않고, 사용자 답변을 받아 다음 요청에 반영함)
  if (!course.courses || course.courses.length === 0) {
    return (
      <p className="whitespace-pre-line text-sm text-gray-600">
        {course.needsClarification && '❓ '}
        {course.message || '조건에 맞는 코스를 찾지 못했어요. 조건을 조금 완화해서 다시 물어봐 주세요.'}
      </p>
    )
  }

  // 결과가 도착하면 지도 + 코스 카드들을 같은 말풍선 안에 표시
  // 카드에 마우스를 올리면 지도가 잠깐 그 코스만 보여주고(미리보기), 클릭하면 그 상태로 고정됨
  // (같은 카드를 다시 클릭하면 고정 해제 → 전체 코스 다시 표시)
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
            grounded={c.grounded}
            groundednessNote={c.groundednessNote}
            color={getCourseColor(index)}
            isActive={activeIndex === index}
            onMouseEnter={() => setHoveredIndex(index)}
            onMouseLeave={() => setHoveredIndex(null)}
            onClick={() => setSelectedIndex((prev) => (prev === index ? null : index))}
          />
        ))}
      </div>

      {/* 돌발 상황 재계산 영역 */}
      <div className="border-t border-gray-100 pt-3">
        {isReplanning ? (
          <p className="flex items-center gap-2 text-sm text-gray-500">
            <span className="h-3 w-3 animate-spin rounded-full border-2 border-gray-300 border-t-[#FEE500]" />
            돌발 상황을 반영해서 코스를 다시 짜는 중이에요...
          </p>
        ) : showDisruptionForm ? (
          <div className="space-y-2">
            <p className="text-xs font-medium text-gray-500">무슨 일이 있었나요?</p>
            <div className="flex flex-wrap gap-1.5">
              {DISRUPTION_PRESETS.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => handleDisruptionSubmit(preset)}
                  className="rounded-full border border-gray-200 bg-white px-2.5 py-1 text-xs text-gray-600 hover:border-[#FEE500] hover:bg-[#FEE500]/10"
                >
                  {preset}
                </button>
              ))}
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleDisruptionSubmit(disruptionReason)
              }}
              className="flex gap-1.5"
            >
              <input
                type="text"
                value={disruptionReason}
                onChange={(e) => setDisruptionReason(e.target.value)}
                placeholder="직접 입력 (예: ○○가 문을 닫았어요)"
                className="flex-1 rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs focus:border-[#FEE500] focus:outline-none"
              />
              <button
                type="submit"
                className="shrink-0 rounded-lg bg-[#FEE500] px-3 text-xs font-bold text-gray-900 hover:bg-[#f5d800]"
              >
                반영
              </button>
              <button
                type="button"
                onClick={() => setShowDisruptionForm(false)}
                className="shrink-0 rounded-lg border border-gray-200 px-2.5 text-xs text-gray-500"
              >
                취소
              </button>
            </form>
          </div>
        ) : (
          <div className="space-y-1.5">
            {disruptionNote && <p className="text-xs text-gray-500">{disruptionNote}</p>}
            <button
              type="button"
              onClick={() => setShowDisruptionForm(true)}
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-bold text-red-600 hover:bg-red-100"
            >
              🚨 돌발 상황 발생! 코스 변경
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
