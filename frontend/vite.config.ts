import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  base: '/',
  build: {
    outDir: 'dist',
  },
  server: {
    port: 5187,
    strictPort: true, // 端口被占用时直接失败，不尝试其他端口
    host: 'localhost'
  }
})