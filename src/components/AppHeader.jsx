// 화면 상단에 공통으로 쓰이는 헤더 컴포넌트
export default function AppHeader({ title, subtitle }) {
  return (
    <header className="mb-8 text-center">
      {/* 서비스 로고/이름 */}
      <span className="mb-2 inline-block rounded-full bg-[#FEE500] px-3 py-1 text-xs font-bold text-gray-900">
        카카오 코스메이트
      </span>
      <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
      {subtitle && (
        <p className="mt-2 text-sm text-gray-500">{subtitle}</p>
      )}
    </header>
  )
}
