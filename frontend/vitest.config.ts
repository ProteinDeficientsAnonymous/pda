import path from 'node:path';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: true,
    // Heavy renders (245-option country <select>, axe passes) are slow but
    // correct; under parallel CI load they trip vitest's 5s default and flake.
    testTimeout: 15000,
    hookTimeout: 15000,
  },
});
