import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Vite 설정: React 플러그인 + Tailwind CSS를 빌드 파이프라인에 연결
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // 임시로 cloudflared 터널(트라이클라우드플레어 도메인)을 통해 접속을 허용하기 위한 설정.
  // 터널 공유가 끝나면 이 항목은 지워도 됩니다 (로컬 개발에는 필요 없음).
  server: {
    allowedHosts: ['.trycloudflare.com'],
  },
})
