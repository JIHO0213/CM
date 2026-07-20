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

      {/* 방문 장소 목록 (place는 이름/좌표/영업시간/리뷰 근거 등을 담은 객체).
          호버/클릭으로 활성화된 카드만 리뷰 근거까지 펼쳐서 보여주고,
          비활성 카드는 이름만 간단히 보여줘서 목록이 너무 길어지지 않게 함. */}
      <ul className="mt-3 space-y-1">
        {places.map((place) =>
          isActive ? (
            <li key={place.name} className="rounded-lg bg-gray-50 p-2 text-sm text-gray-700">
              <div className="flex items-center gap-1.5">
                <span className="font-medium">📍 {place.name}</span>
              </div>
              {place.hours && <p className="mt-0.5 text-xs text-gray-400">🕐 {place.hours}</p>}
              {place.reviewSnippet && (
                <p className="mt-1 text-xs italic text-gray-500">"{place.reviewSnippet}"</p>
              )}
              {place.matchedConstraints?.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {place.matchedConstraints.map((keyword) => (
                    <span
                      key={keyword}
                      className="rounded-full bg-[#FEE500]/40 px-2 py-0.5 text-[10px] font-medium text-gray-700"
                    >
                      {keyword}
                    </span>
                  ))}
                </div>
              )}
            </li>
          ) : (
            <li key={place.name} className="text-sm text-gray-700">
              📍 {place.name}
            </li>
          )
        )}
      </ul>
    </article>
  )
}
