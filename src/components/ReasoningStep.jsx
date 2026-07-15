// 추론 단계 하나를 보여주는 컴포넌트
export default function ReasoningStep({ stepNumber, text, isVisible }) {
  return (
    <div
      className={`flex items-center gap-3 rounded-lg border px-4 py-3 transition-all duration-500 ${
        isVisible
          ? 'border-[#FEE500] bg-white opacity-100'
          : 'border-transparent bg-transparent opacity-0'
      }`}
    >
      {/* 단계 번호 원형 뱃지 */}
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#FEE500] text-sm font-bold">
        {stepNumber}
      </span>
      {/* 단계 설명 텍스트 */}
      <p className="text-sm text-gray-700">{text}</p>
    </div>
  )
}
