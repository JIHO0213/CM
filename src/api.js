// mock JSON 파일들을 미리 import (Vite가 빌드 시 번들에 포함)
import case1 from './mock/case1.json'
import case2 from './mock/case2.json'
import case3 from './mock/case3.json'

// true면 mock 데이터 사용, false면 실제 API 호출
export const USE_MOCK = true

// caseId별 mock 데이터를 담은 객체
const mockDataMap = {
  case1,
  case2,
  case3,
}

/**
 * 코스 추천 데이터를 가져오는 함수
 * @param {string} caseId - 'case1' | 'case2' | 'case3'
 * @returns {Promise<object>} 추천 코스 데이터
 */
export async function getCourseRecommendation(caseId) {
  if (USE_MOCK) {
    // mock 모드: 해당 caseId의 JSON을 반환
    const data = mockDataMap[caseId]
    if (!data) {
      throw new Error(`Mock 데이터를 찾을 수 없습니다: ${caseId}`)
    }
    // 실제 API처럼 비동기로 동작하도록 약간의 딜레이 추가
    return new Promise((resolve) => {
      setTimeout(() => resolve(data), 300)
    })
  }

  // 실제 API 모드: 나중에 이 부분만 수정하면 됩니다
  const response = await fetch(`/api/recommendations/${caseId}`)
  if (!response.ok) {
    throw new Error('API 요청 실패')
  }
  return response.json()
}
