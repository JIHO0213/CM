// 코스별 색상 (지도 경로선 + 코스 카드 표시에 공통으로 사용)
// A안=파랑, B안=초록, C안=주황
export const COURSE_COLORS = ['#3B82F6', '#22C55E', '#F97316']

// courses 배열 안에서의 순서(index)로 색상을 가져오는 함수
export function getCourseColor(index) {
  return COURSE_COLORS[index % COURSE_COLORS.length]
}
