import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const BACKEND_URL =
  process.env.VITE_BACKEND_URL || 'https://personalised-trainer.onrender.com';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/ws': {
        target: process.env.VITE_WS_PROXY_TARGET || BACKEND_URL,
        ws: true,
        changeOrigin: true,
      },
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET || BACKEND_URL,
        changeOrigin: true,
      },
    },
  },
});
