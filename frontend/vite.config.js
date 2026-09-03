import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// 开发环境将 /api 和 /uploads 转发到后端，避免跨域
// 后端地址可用环境变量 VITE_PROXY_TARGET 覆盖（前后端不在同一台机器时使用），默认本机 8000
// 生产环境由 FastAPI 单端口托管，无需代理
const backendTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [
    vue(),
    // 阶段四：Element Plus 按需引入（组件自动注册 + ElMessage 等 API 自动导入）
    AutoImport({
      resolvers: [ElementPlusResolver()],
      // JS 项目无需生成 .d.ts，关闭避免噪音
      dts: false
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: false
    })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true
      },
      '/uploads': {
        target: backendTarget,
        changeOrigin: true
      }
    }
  },
  build: {
    // 不让 vite 自动清空 dist（沙箱对批量删除旧产物有限制）；
    // 旧 hash 文件会残留但不影响运行（index.html 只引用新 chunk），建议定期手动清理
    emptyOutDir: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-vue': ['vue', 'vue-router', 'pinia', 'axios'],
          'vendor-flow': ['@vue-flow/core', '@vue-flow/background', '@vue-flow/controls', '@vue-flow/minimap']
        }
      }
    }
  }
})
