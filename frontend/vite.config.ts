import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    server: {
      host: '0.0.0.0',  // 允许内网访问
      port: 5173,
      cors: true,
      // Vite Proxy 配置：将 /api 请求转发到后端
      proxy: {
        '/api': {
          target: 'http://localhost:8011',  // 后端服务地址
          changeOrigin: true,                // 修改请求头中的 origin
          secure: false,                     // 不验证 SSL 证书
          // 不需要 rewrite，因为前端请求是 /api/v1/xxx，后端也是 /api/v1/xxx
        }
      }
    }
  }
})
