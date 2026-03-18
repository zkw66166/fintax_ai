import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        timeout: 300000,      // 5 min — SSE streams need long timeouts
        proxyTimeout: 300000,  // 5 min — proxy socket timeout
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
