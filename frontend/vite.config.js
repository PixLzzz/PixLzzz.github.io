import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Relative base so the build works on GitHub Pages regardless of repo name
  base: './',
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
