import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  server: {
    port: 3040,
    host: '0.0.0.0',
    cors: true,
  },
  preview: {
    port: 5014,
    host: '0.0.0.0',
    cors: true,
  },
  plugins: [react()],
})
