import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { BACKEND_URL } from './src/config.js';

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
