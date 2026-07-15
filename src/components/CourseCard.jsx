// 결과 화면에서 코스 하나를 보여주는 카드 컴포넌트
// color: 지도 경로선과 맞춘 이 코스의 색상 (마우스 올리거나 클릭하면 카드 테두리도 이 색으로 강조됨)
export default function CourseCard({
  title,
  description,
  duration,
  places,
  index,
  color,
  isActive,
  onMouseEnter,
  onMouseLeave,
  onClick,
}) {
  return (
    <article
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      onClick={onClick}
      className={`cursor-pointer rounded-xl border bg-white p-5 shadow-sm transition ${
        isActive ? 'shadow-md' : 'border-gray-200'
      }`}
      style={isActive ? { borderColor: color, borderWidth: 2 } : undefined}
    >
      {/* 코스 번호 뱃지 (색 점으로 지도 경로선과 매칭) */}
      <span className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-[#FEE500] px-3 py-1 text-xs font-bold text-gray-900">
        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
        코스 {index}
      </span>

      {/* 코스 제목 */}
      <h3 className="text-lg font-bold text-gray-900">{title}</h3>

      {/* 코스 설명 */}
      <p className="mt-2 text-sm text-gray-600">{description}</p>

      {/* 예상 소요 시간 */}
      <p className="mt-3 text-xs font-medium text-gray-400">⏱ {duration}</p>

      {/* 방문 장소 목록 (place는 이름/좌표/영업시간 등을 담은 객체) */}
      <ul className="mt-3 space-y-1">
        {places.map((place) => (
          <li key={place.name} className="text-sm text-gray-700">
            📍 {place.name}
          </li>
        ))}
      </ul>
    </article>
  )
}
