import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/jobs': 'http://127.0.0.1:8000',
      '/swipes': 'http://127.0.0.1:8000',
      '/stats': 'http://127.0.0.1:8000',
      '/contacts': 'http://127.0.0.1:8000',
      '/outreach': 'http://127.0.0.1:8000',
      '/cv': 'http://127.0.0.1:8000',
      '/applications': 'http://127.0.0.1:8000',
    }
  }
})