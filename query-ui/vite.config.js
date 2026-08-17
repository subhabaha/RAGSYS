import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/query/',
  build: { outDir: 'dist' },
  server: { port: 5174 }
});
