import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  build: {
    outDir: '../backend/static/dist',
    emptyOutDir: true,
    assetsDir: 'assets',
    rollupOptions: {
      output: {
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router', 'axios'],
        },
      },
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    allowedHosts: ['market.gyx-a.cn'],
    proxy: {
      '/api': 'http://localhost:8000',
      '/static': 'http://localhost:8000',
    },
  },
})