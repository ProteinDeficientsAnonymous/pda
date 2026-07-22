import path from 'node:path';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const backendTarget = `http://localhost:${process.env.BACKEND_PORT ?? 8000}`;

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      // SSE endpoint — disable proxy buffering so events stream through
      // in real time instead of getting held until connection close.
      '/api/notifications/stream': {
        target: backendTarget,
        changeOrigin: true,
        selfHandleResponse: false,
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            proxyRes.headers['x-accel-buffering'] = 'no';
            proxyRes.headers['cache-control'] = 'no-cache';
          });
        },
      },
      '/api': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/media': {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
