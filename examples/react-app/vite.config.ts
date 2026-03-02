import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/keycloak-admin': {
        target: 'http://localhost:8080',
        rewrite: (path) => path.replace(/^\/keycloak-admin/, '/admin'),
        changeOrigin: true,
      },
    },
  },
})
