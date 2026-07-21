// mock JSON 파일들을 미리 import (Vite가 빌드 시 번들에 포함)
import case1 from './mock/case1.json'
import case2 from './mock/case2.json'
import case3 from './mock/case3.json'

// true면 mock 데이터 사용, false면 실제 백엔드(/api/courses) 호출
export const USE_MOCK = false

// 백엔드 주소. .env의 VITE_API_BASE_URL로 바꿀 수 있음 (기본값: 로컬 백엔드)
// exe 배포판처럼 프론트/백엔드가 같은 서버·같은 포트에서 서빙될 때는
// VITE_API_BASE_URL=""(빈 문자열)로 빌드해서 상대 경로(같은 origin)로 요청하게 함.
// "??"를 써야 빈 문자열이 살아남음 (||였으면 빈 문자열도 falsy라 기본값으로 덮임).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

// caseId별 mock 데이터를 담은 객체 (USE_MOCK=true일 때만 사용)
const mockDataMap = {
  case1,
  case2,
  case3,
}

/**
 * 코스 추천 데이터를 가져오는 함수
 * @param {object} params
 * @param {string} params.query - 사용자가 입력한 자유 문장 (실제 백엔드 호출에 사용)
 * @param {string} params.caseId - 'case1' | 'case2' | 'case3' (mock 모드에서만 사용)
 * @returns {Promise<object>} { title, courses } 또는 { title: null, courses: [], message } (조건에 안 맞을 때)
 */
export async function getCourseRecommendation({ query, caseId, mustIncludePlace }) {
  if (USE_MOCK) {
    const data = mockDataMap[caseId]
    if (!data) {
      throw new Error(`Mock 데이터를 찾을 수 없습니다: ${caseId}`)
    }
    // 실제 API처럼 비동기로 동작하도록 약간의 딜레이 추가
    return new Promise((resolve) => {
      setTimeout(() => resolve(data), 300)
    })
  }

  // 실제 백엔드 호출
  const response = await fetch(`${API_BASE_URL}/api/courses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      ...(mustIncludePlace ? { must_include_place: mustIncludePlace } : {}),
    }),
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    // 백엔드는 에러를 { "error": "..." } 형태로 반환함
    throw new Error(data?.error || 'API 요청에 실패했습니다')
  }

  // 성공 시: { title, courses: [...] }
  // 조건에 맞는 코스가 없을 때: { title: null, courses: [], message: "..." }
  return data
}

/**
 * 코스 추천을 SSE로 스트리밍 받아옴. 로딩 UI(STEP 인디케이터)가 고정 타이머가 아니라
 * 백엔드가 실제로 어느 단계를 처리 중인지에 맞춰 갱신되도록 하기 위한 용도.
 * (네이티브 EventSource는 POST 바디를 못 보내서, fetch + ReadableStream으로 직접 파싱함)
 * @param {object} params
 * @param {string} params.query
 * @param {object} [params.mustIncludePlace] - /api/parse-image가 반환한 { name, lat, lng, address }
 *   (SNS 캡처 이미지에서 인식되고, 가게 데이터에도 있는 걸로 검증된 장소일 때만 넘김)
 * @param {(step: number) => void} [params.onStep] - 새 단계가 시작될 때마다 호출 (1~5)
 * @param {(data: object) => void} params.onResult - 최종 결과 도착 시 호출
 *   ({ title, courses } | { title: null, courses: [], message } | { error })
 * @param {AbortSignal} [params.signal]
 */
export async function streamCourseRecommendation({ query, mustIncludePlace, onStep, onResult, signal }) {
  const response = await fetch(`${API_BASE_URL}/api/courses/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      ...(mustIncludePlace ? { must_include_place: mustIncludePlace } : {}),
    }),
    signal,
  })

  if (!response.ok || !response.body) {
    throw new Error('API 요청에 실패했습니다')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    // sse_starlette는 줄바꿈으로 \r\n을 쓰므로(SSE 스펙 기본값), \n으로 통일해서 버퍼에 쌓음
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')

    // SSE 이벤트는 빈 줄(\n\n)로 구분되고, 각 이벤트는 "event: ...", "data: ..." 줄로 구성됨
    let boundary
    while ((boundary = buffer.indexOf('\n\n')) !== -1) {
      const rawEvent = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)

      const lines = rawEvent.split('\n')
      const eventLine = lines.find((line) => line.startsWith('event:'))
      const dataLine = lines.find((line) => line.startsWith('data:'))
      if (!eventLine || !dataLine) continue

      const eventType = eventLine.slice('event:'.length).trim()
      const data = JSON.parse(dataLine.slice('data:'.length).trim())

      if (eventType === 'step') {
        onStep?.(data.step)
      } else if (eventType === 'result') {
        onResult?.(data)
      }
    }
  }
}

/**
 * SNS 캡처 이미지를 업로드해서 상호명/주소/좌표를 인식.
 * 첫 요청 시에만 쓰는 'SNS 캡처로 가게 추가' 버튼이 이 함수를 호출함.
 * @param {File} file - 업로드한 이미지 파일
 * @returns {Promise<object>} { name, address, notes, lat, lng, is_known_store }
 *   is_known_store가 false면 우리 가게 데이터에 없는 곳이라 코스에 반영하면 안 됨.
 */
export async function parseImage(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/parse-image`, {
    method: 'POST',
    body: formData,
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(data?.error || '이미지 분석에 실패했습니다')
  }

  return data
}

/**
 * 돌발 상황(비, 임시휴무 등) 발생 시 코스 재계산
 * @param {object} params
 * @param {string} params.query - 원래 사용자가 입력했던 문장 (그대로 다시 보냄)
 * @param {string} params.disruptionReason - 예: "갑자기 비가 와요", "가게가 문을 닫았어요"
 * @param {string} [params.excludePlaceName] - 문제가 된 특정 장소 이름 (있으면 다음 후보로 자동 교체)
 * @returns {Promise<object>} { title, courses, disruption_reason } 형태 (기본 응답과 동일 + disruption_reason)
 */
export async function replanCourses({ query, disruptionReason, excludePlaceName }) {
  if (USE_MOCK) {
    // mock 모드에선 그냥 같은 케이스 데이터를 그대로 다시 반환 (재계산 흉내만 냄)
    return new Promise((resolve) => {
      setTimeout(() => resolve(mockDataMap.case1), 300)
    })
  }

  const response = await fetch(`${API_BASE_URL}/api/courses/replan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      disruption_reason: disruptionReason,
      exclude_place_name: excludePlaceName || null,
    }),
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(data?.error || 'API 요청에 실패했습니다')
  }

  return data
}
