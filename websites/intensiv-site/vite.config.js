import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';
import { BASE_PATH } from './src/config.js';

// GitHub Pages отдаёт сайт из main:/docs по адресу /ai-na-zakaz-intensiv/.
// Страницы index.html и privacy/ генерирует scripts/build-pages.mjs из src/template.html и src/privacy.html.
export default defineConfig({
  base: BASE_PATH,
  plugins: [tailwindcss()],
  build: {
    outDir: 'docs',
    emptyOutDir: true,
    assetsInlineLimit: 0,
    rollupOptions: {
      input: {
        main: resolve(import.meta.dirname, 'index.html'),
        privacy: resolve(import.meta.dirname, 'privacy/index.html'),
      },
    },
  },
});
