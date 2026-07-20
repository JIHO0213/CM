// 추론 단계 하나를 보여주는 컴포넌트
// status: 'pending'(아직 안 옴, 안 보임) | 'running'(지금 이 단계 처리 중, 스피너) | 'done'(완료)
export default function ReasoningStep({ stepNumber, text, status }) {
  const isVisible = status !== 'pending'

  return (
    <div
      className={`flex items-center gap-3 rounded-lg border px-4 py-3 transition-all duration-500 ${
        isVisible
          ? 'border-[#FEE500] bg-white opacity-100'
          : 'border-transparent bg-transparent opacity-0'
      }`}
    >
      {/* 단계 번호 원형 뱃지: 진행 중인 단계만 스피너로 표시해서 "지금 뭘 하고 있는지" 보여줌 */}
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#FEE500] text-sm font-bold">
        {status === 'running' ? (
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-gray-500 border-t-transparent" />
        ) : (
          stepNumber
        )}
      </span>
      {/* 단계 설명 텍스트: 완료된 단계는 살짝 흐리게 처리해 지금 단계와 구분 */}
      <p className={`text-sm ${status === 'done' ? 'text-gray-400' : 'text-gray-700'}`}>{text}</p>
    </div>
  )
}
