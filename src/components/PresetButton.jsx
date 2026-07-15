// 프리셋 케이스 선택 버튼 컴포넌트
export default function PresetButton({ label, description, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-xl border border-gray-200 bg-white p-4 text-left shadow-sm transition hover:border-[#FEE500] hover:shadow-md"
    >
      {/* 케이스 제목 */}
      <span className="block font-semibold text-gray-900">{label}</span>
      {/* 케이스 설명 (한 줄 요약) */}
      <span className="mt-1 block text-sm text-gray-500">{description}</span>
    </button>
  )
}
