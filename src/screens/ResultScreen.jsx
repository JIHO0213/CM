import { Link } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import CourseCard from '../components/CourseCard'
import MapPlaceholder from '../components/MapPlaceholder'

// 결과 화면에 표시할 더미 코스 데이터 (다음 단계에서 api.js로 교체)
const DUMMY_COURSES = [
  {
    id: 1,
    title: '감성 카페 산책 코스',
    description: '연남동 골목 카페 → 망원 한강공원 산책 → 저녁 와인바',
    duration: '약 4시간',
    places: ['연남동 카페거리', '망원 한강공원', '홍대 와인바'],
  },
  {
    id: 2,
    title: '맛집 투어 코스',
    description: '브런치 카페 → 일본 라멘 → 디저트 카페',
    duration: '약 3시간',
    places: ['홍대 브런치 카페', '합정 라멘집', '상수 디저트 카페'],
  },
  {
    id: 3,
    title: '문화 체험 코스',
    description: '전시 관람 → 빈티지 숍 → 재즈바',
    duration: '약 5시간',
    places: ['DMC 전시관', '연남 빈티지 숍', '홍대 재즈바'],
  },
]

export default function ResultScreen() {
  return (
    <div className="mx-auto min-h-screen max-w-lg px-4 py-10">
      <AppHeader
        title="추천 코스 3가지"
        subtitle="마음에 드는 코스를 선택해보세요"
      />

      {/* 카카오맵 자리 (다음 단계에서 SDK 연동) */}
      <section className="mb-6">
        <MapPlaceholder />
      </section>

      {/* 코스 카드 3개 나열 */}
      <section className="space-y-4">
        {DUMMY_COURSES.map((course, index) => (
          <CourseCard
            key={course.id}
            index={index + 1}
            title={course.title}
            description={course.description}
            duration={course.duration}
            places={course.places}
          />
        ))}
      </section>

      {/* 처음으로 돌아가기 버튼 */}
      <Link
        to="/"
        className="mt-8 block w-full rounded-xl border border-gray-200 bg-white py-3 text-center text-sm font-medium text-gray-700 transition hover:bg-gray-50"
      >
        다시 추천 받기
      </Link>
    </div>
  )
}
