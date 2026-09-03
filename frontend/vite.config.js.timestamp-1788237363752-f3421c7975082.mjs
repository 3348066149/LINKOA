// vite.config.js
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "file:///E:/BaiduNetdiskDownload/LINKOA/frontend/node_modules/vite/dist/node/index.js";
import vue from "file:///E:/BaiduNetdiskDownload/LINKOA/frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs";
import AutoImport from "file:///E:/BaiduNetdiskDownload/LINKOA/frontend/node_modules/unplugin-auto-import/dist/vite.mjs";
import Components from "file:///E:/BaiduNetdiskDownload/LINKOA/frontend/node_modules/unplugin-vue-components/dist/vite.mjs";
import { ElementPlusResolver } from "file:///E:/BaiduNetdiskDownload/LINKOA/frontend/node_modules/unplugin-vue-components/dist/resolvers.mjs";
var __vite_injected_original_import_meta_url = "file:///E:/BaiduNetdiskDownload/LINKOA/frontend/vite.config.js";
var backendTarget = process.env.VITE_PROXY_TARGET || "http://localhost:8000";
var vite_config_default = defineConfig({
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
      "@": fileURLToPath(new URL("./src", __vite_injected_original_import_meta_url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: backendTarget,
        changeOrigin: true
      },
      "/uploads": {
        target: backendTarget,
        changeOrigin: true
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-vue": ["vue", "vue-router", "pinia", "axios"],
          "vendor-flow": ["@vue-flow/core", "@vue-flow/background", "@vue-flow/controls", "@vue-flow/minimap"]
        }
      }
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJFOlxcXFxCYWlkdU5ldGRpc2tEb3dubG9hZFxcXFxMSU5LT0FcXFxcZnJvbnRlbmRcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIkU6XFxcXEJhaWR1TmV0ZGlza0Rvd25sb2FkXFxcXExJTktPQVxcXFxmcm9udGVuZFxcXFx2aXRlLmNvbmZpZy5qc1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vRTovQmFpZHVOZXRkaXNrRG93bmxvYWQvTElOS09BL2Zyb250ZW5kL3ZpdGUuY29uZmlnLmpzXCI7aW1wb3J0IHsgZmlsZVVSTFRvUGF0aCwgVVJMIH0gZnJvbSAnbm9kZTp1cmwnXG5pbXBvcnQgeyBkZWZpbmVDb25maWcgfSBmcm9tICd2aXRlJ1xuaW1wb3J0IHZ1ZSBmcm9tICdAdml0ZWpzL3BsdWdpbi12dWUnXG5pbXBvcnQgQXV0b0ltcG9ydCBmcm9tICd1bnBsdWdpbi1hdXRvLWltcG9ydC92aXRlJ1xuaW1wb3J0IENvbXBvbmVudHMgZnJvbSAndW5wbHVnaW4tdnVlLWNvbXBvbmVudHMvdml0ZSdcbmltcG9ydCB7IEVsZW1lbnRQbHVzUmVzb2x2ZXIgfSBmcm9tICd1bnBsdWdpbi12dWUtY29tcG9uZW50cy9yZXNvbHZlcnMnXG5cbi8vIFx1NUYwMFx1NTNEMVx1NzNBRlx1NTg4M1x1NUMwNiAvYXBpIFx1NTQ4QyAvdXBsb2FkcyBcdThGNkNcdTUzRDFcdTUyMzBcdTU0MEVcdTdBRUZcdUZGMENcdTkwN0ZcdTUxNERcdThERThcdTU3REZcbi8vIFx1NTQwRVx1N0FFRlx1NTczMFx1NTc0MFx1NTNFRlx1NzUyOFx1NzNBRlx1NTg4M1x1NTNEOFx1OTFDRiBWSVRFX1BST1hZX1RBUkdFVCBcdTg5ODZcdTc2RDZcdUZGMDhcdTUyNERcdTU0MEVcdTdBRUZcdTRFMERcdTU3MjhcdTU0MENcdTRFMDBcdTUzRjBcdTY3M0FcdTU2NjhcdTY1RjZcdTRGN0ZcdTc1MjhcdUZGMDlcdUZGMENcdTlFRDhcdThCQTRcdTY3MkNcdTY3M0EgODAwMFxuLy8gXHU3NTFGXHU0RUE3XHU3M0FGXHU1ODgzXHU3NTMxIEZhc3RBUEkgXHU1MzU1XHU3QUVGXHU1M0UzXHU2MjU4XHU3QkExXHVGRjBDXHU2NUUwXHU5NzAwXHU0RUUzXHU3NDA2XG5jb25zdCBiYWNrZW5kVGFyZ2V0ID0gcHJvY2Vzcy5lbnYuVklURV9QUk9YWV9UQVJHRVQgfHwgJ2h0dHA6Ly9sb2NhbGhvc3Q6ODAwMCdcblxuZXhwb3J0IGRlZmF1bHQgZGVmaW5lQ29uZmlnKHtcbiAgcGx1Z2luczogW1xuICAgIHZ1ZSgpLFxuICAgIC8vIFx1OTYzNlx1NkJCNVx1NTZEQlx1RkYxQUVsZW1lbnQgUGx1cyBcdTYzMDlcdTk3MDBcdTVGMTVcdTUxNjVcdUZGMDhcdTdFQzRcdTRFRjZcdTgxRUFcdTUyQThcdTZDRThcdTUxOEMgKyBFbE1lc3NhZ2UgXHU3QjQ5IEFQSSBcdTgxRUFcdTUyQThcdTVCRkNcdTUxNjVcdUZGMDlcbiAgICBBdXRvSW1wb3J0KHtcbiAgICAgIHJlc29sdmVyczogW0VsZW1lbnRQbHVzUmVzb2x2ZXIoKV0sXG4gICAgICAvLyBKUyBcdTk4NzlcdTc2RUVcdTY1RTBcdTk3MDBcdTc1MUZcdTYyMTAgLmQudHNcdUZGMENcdTUxNzNcdTk1RURcdTkwN0ZcdTUxNERcdTU2NkFcdTk3RjNcbiAgICAgIGR0czogZmFsc2VcbiAgICB9KSxcbiAgICBDb21wb25lbnRzKHtcbiAgICAgIHJlc29sdmVyczogW0VsZW1lbnRQbHVzUmVzb2x2ZXIoKV0sXG4gICAgICBkdHM6IGZhbHNlXG4gICAgfSlcbiAgXSxcbiAgcmVzb2x2ZToge1xuICAgIGFsaWFzOiB7XG4gICAgICAnQCc6IGZpbGVVUkxUb1BhdGgobmV3IFVSTCgnLi9zcmMnLCBpbXBvcnQubWV0YS51cmwpKVxuICAgIH1cbiAgfSxcbiAgc2VydmVyOiB7XG4gICAgcG9ydDogNTE3MyxcbiAgICBwcm94eToge1xuICAgICAgJy9hcGknOiB7XG4gICAgICAgIHRhcmdldDogYmFja2VuZFRhcmdldCxcbiAgICAgICAgY2hhbmdlT3JpZ2luOiB0cnVlXG4gICAgICB9LFxuICAgICAgJy91cGxvYWRzJzoge1xuICAgICAgICB0YXJnZXQ6IGJhY2tlbmRUYXJnZXQsXG4gICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZVxuICAgICAgfVxuICAgIH1cbiAgfSxcbiAgYnVpbGQ6IHtcbiAgICByb2xsdXBPcHRpb25zOiB7XG4gICAgICBvdXRwdXQ6IHtcbiAgICAgICAgbWFudWFsQ2h1bmtzOiB7XG4gICAgICAgICAgJ3ZlbmRvci12dWUnOiBbJ3Z1ZScsICd2dWUtcm91dGVyJywgJ3BpbmlhJywgJ2F4aW9zJ10sXG4gICAgICAgICAgJ3ZlbmRvci1mbG93JzogWydAdnVlLWZsb3cvY29yZScsICdAdnVlLWZsb3cvYmFja2dyb3VuZCcsICdAdnVlLWZsb3cvY29udHJvbHMnLCAnQHZ1ZS1mbG93L21pbmltYXAnXVxuICAgICAgICB9XG4gICAgICB9XG4gICAgfVxuICB9XG59KVxuIl0sCiAgIm1hcHBpbmdzIjogIjtBQUErUyxTQUFTLGVBQWUsV0FBVztBQUNsVixTQUFTLG9CQUFvQjtBQUM3QixPQUFPLFNBQVM7QUFDaEIsT0FBTyxnQkFBZ0I7QUFDdkIsT0FBTyxnQkFBZ0I7QUFDdkIsU0FBUywyQkFBMkI7QUFMeUosSUFBTSwyQ0FBMkM7QUFVOU8sSUFBTSxnQkFBZ0IsUUFBUSxJQUFJLHFCQUFxQjtBQUV2RCxJQUFPLHNCQUFRLGFBQWE7QUFBQSxFQUMxQixTQUFTO0FBQUEsSUFDUCxJQUFJO0FBQUE7QUFBQSxJQUVKLFdBQVc7QUFBQSxNQUNULFdBQVcsQ0FBQyxvQkFBb0IsQ0FBQztBQUFBO0FBQUEsTUFFakMsS0FBSztBQUFBLElBQ1AsQ0FBQztBQUFBLElBQ0QsV0FBVztBQUFBLE1BQ1QsV0FBVyxDQUFDLG9CQUFvQixDQUFDO0FBQUEsTUFDakMsS0FBSztBQUFBLElBQ1AsQ0FBQztBQUFBLEVBQ0g7QUFBQSxFQUNBLFNBQVM7QUFBQSxJQUNQLE9BQU87QUFBQSxNQUNMLEtBQUssY0FBYyxJQUFJLElBQUksU0FBUyx3Q0FBZSxDQUFDO0FBQUEsSUFDdEQ7QUFBQSxFQUNGO0FBQUEsRUFDQSxRQUFRO0FBQUEsSUFDTixNQUFNO0FBQUEsSUFDTixPQUFPO0FBQUEsTUFDTCxRQUFRO0FBQUEsUUFDTixRQUFRO0FBQUEsUUFDUixjQUFjO0FBQUEsTUFDaEI7QUFBQSxNQUNBLFlBQVk7QUFBQSxRQUNWLFFBQVE7QUFBQSxRQUNSLGNBQWM7QUFBQSxNQUNoQjtBQUFBLElBQ0Y7QUFBQSxFQUNGO0FBQUEsRUFDQSxPQUFPO0FBQUEsSUFDTCxlQUFlO0FBQUEsTUFDYixRQUFRO0FBQUEsUUFDTixjQUFjO0FBQUEsVUFDWixjQUFjLENBQUMsT0FBTyxjQUFjLFNBQVMsT0FBTztBQUFBLFVBQ3BELGVBQWUsQ0FBQyxrQkFBa0Isd0JBQXdCLHNCQUFzQixtQkFBbUI7QUFBQSxRQUNyRztBQUFBLE1BQ0Y7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUNGLENBQUM7IiwKICAibmFtZXMiOiBbXQp9Cg==
