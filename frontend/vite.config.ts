import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      // Any request starting with /api will be proxied to FastAPI, so the browser
      // only ever sees this origin and the backend's auth cookie stays
      // first-party. vercel.json mirrors this rewrite in production — keep the
      // two in step, or the HttpOnly session breaks in one environment only.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})