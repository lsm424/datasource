import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// 自定义插件：禁用Vite的轮询重启机制
const disablePollingPlugin = () => {
  return {
    name: 'disable-polling',
    configureServer(server) {
      // 只禁用WebSocket，保留watcher供其他插件使用
      if (server.ws) {
        server.ws.close()
        server.ws = null
      }
    }
  }
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: true,
    }),
    Components({
      resolvers: [ElementPlusResolver({
        importStyle: false
      })],
    }),
    // 添加自定义插件
    disablePollingPlugin(),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    host: true,
    // 完全禁用HMR功能
    hmr: false,
    // 禁用文件变化时的自动刷新
    watch: {
      usePolling: false,
      ignored: ['**/node_modules/**', '**/.git/**']
    },
    // 增加超时时间
    timeout: 30000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api/v1'),
        // 增加代理超时时间
        timeout: 30000,
        configure: (proxy, options) => {
          // 代理配置
        }
      },
    },
  },
  build: {
    target: 'esnext',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
  },
})
