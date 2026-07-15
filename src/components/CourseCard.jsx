// 결과 화면에서 코스 하나를 보여주는 카드 컴포넌트
export default function CourseCard({ title, description, duration, places, index }) {
  return (
    <article className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      {/* 코스 번호 뱃지 */}
      <span className="mb-3 inline-block rounded-full bg-[#FEE500] px-3 py-1 text-xs font-bold text-gray-900">
        코스 {index}
      </span>

      {/* 코스 제목 */}
      <h3 className="text-lg font-bold text-gray-900">{title}</h3>

      {/* 코스 설명 */}
      <p className="mt-2 text-sm text-gray-600">{description}</p>

      {/* 예상 소요 시간 */}
      <p className="mt-3 text-xs font-medium text-gray-400">⏱ {duration}</p>

      {/* 방문 장소 목록 */}
      <ul className="mt-3 space-y-1">
        {places.map((place) => (
          <li key={place} className="text-sm text-gray-700">
            📍 {place}
          </li>
        ))}
      </ul>
    </article>
  )
}
