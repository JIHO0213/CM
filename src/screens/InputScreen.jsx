import { useNavigate } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import PresetButton from '../components/PresetButton'

// 프리셋 케이스 3개의 정보 (버튼에 표시할 텍스트)
const PRESET_CASES = [
  {
    id: 'case1',
    label: '홍대 데이트',
    description: '홍대에서 데이트하기 좋은 곳 추천',
  },
  {
    id: 'case2',
    label: '강남 회식',
    description: '강남에서 팀 회식 장소 추천',
  },
  {
    id: 'case3',
    label: '제주 여행',
    description: '제주도 2박 3일 여행 코스',
  },
]

export default function InputScreen() {
  // useNavigate: 다른 화면(경로)으로 이동할 때 사용
  const navigate = useNavigate()

  // 프리셋 버튼 클릭 시 추론 화면으로 이동 (로직은 다음 단계에서 추가)
  const handlePresetClick = (caseId) => {
    navigate('/reasoning', { state: { caseId } })
  }

  // 자유 입력 제출 시 추론 화면으로 이동 (로직은 다음 단계에서 추가)
  const handleSubmit = (e) => {
    e.preventDefault()
    navigate('/reasoning')
  }

  return (
    <div className="mx-auto min-h-screen max-w-lg px-4 py-10">
      <AppHeader
        title="어디로 갈까요?"
        subtitle="프리셋을 선택하거나 직접 입력해보세요"
      />

      {/* 프리셋 케이스 버튼 3개 */}
      <section className="space-y-3">
        {PRESET_CASES.map((preset) => (
          <PresetButton
            key={preset.id}
            label={preset.label}
            description={preset.description}
            onClick={() => handlePresetClick(preset.id)}
          />
        ))}
      </section>

      {/* 구분선 */}
      <div className="my-6 flex items-center gap-3">
        <div className="h-px flex-1 bg-gray-200" />
        <span className="text-xs text-gray-400">또는</span>
        <div className="h-px flex-1 bg-gray-200" />
      </div>

      {/* 자유 입력창 */}
      <form onSubmit={handleSubmit}>
        <label htmlFor="freeInput" className="mb-2 block text-sm font-medium text-gray-700">
          자유 입력
        </label>
        <textarea
          id="freeInput"
          rows={3}
          placeholder="예: 성수동에서 브런치 먹고 갤러리 가고 싶어"
          className="w-full rounded-xl border border-gray-200 p-3 text-sm focus:border-[#FEE500] focus:outline-none"
        />
        <button
          type="submit"
          className="mt-3 w-full rounded-xl bg-[#FEE500] py-3 text-sm font-bold text-gray-900 transition hover:bg-[#f5d800]"
        >
          코스 추천 받기
        </button>
      </form>
    </div>
  )
}
