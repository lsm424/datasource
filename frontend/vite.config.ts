/*
 * @Author: wadesmli
 * @Date: 2026-03-02 12:45:38
 * @LastEditors: wadesmli
 * @LastEditTime: 2026-04-14 11:02:37
 * @FilePath: vite.config.ts
 * @Description: 
 * 
 * Copyright (c) 2026 by wadesmli, All Rights Reserved. 
 */
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

// 自定义插件：记录访问日志
const accessLogPlugin = () => {
  return {
    name: 'access-log',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const start = Date.now()
        const url = req.url
        const method = req.method
        const ip = req.headers['x-forwarded-for'] || req.headers['x-real-ip'] || req.socket.remoteAddress

        res.on('finish', () => {
          const duration = Date.now() - start
          const status = res.statusCode
          const timestamp = new Date().toLocaleString()
          console.log(`[${timestamp}] ${method} ${url} - ${status} - ${duration}ms - IP: ${ip}`)
        })

        next()
      })
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
    accessLogPlugin(),
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
    allowedHosts: ['falsk.e8.luyouxia.net'],
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
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
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
