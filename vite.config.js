import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Vite 설정: React 플러그인 + Tailwind CSS를 빌드 파이프라인에 연결
export default defineConfig({
  plugins: [react(), tailwindcss()],
})
