// 카카오맵 SDK가 들어갈 자리 (지금은 빈 박스로 표시)
export default function MapPlaceholder() {
  return (
    <div className="flex h-48 items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-gray-100">
      <div className="text-center">
        {/* 지도 아이콘 대용 텍스트 */}
        <p className="text-2xl">🗺️</p>
        <p className="mt-2 text-sm text-gray-500">카카오맵 영역 (다음 단계에서 연동)</p>
      </div>
    </div>
  )
}
