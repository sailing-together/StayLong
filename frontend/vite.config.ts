import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiProxy = {
  '/v1': {
    target: process.env.STAYLONG_API_PROXY_TARGET ?? 'http://127.0.0.1:8000',
    changeOrigin: true,
    headers: process.env.STAYLONG_API_PROXY_TOKEN
      ? { 'X-StayLong-API-Token': process.env.STAYLONG_API_PROXY_TOKEN }
      : undefined,
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: { proxy: apiProxy },
})
