import { defineConfig } from 'vite';
export default defineConfig(({ mode }) => mode === 'background' || mode === 'content' ? {
  define: { 'process.env.NODE_ENV': JSON.stringify('production') },
  build: { minify: true, emptyOutDir: false, lib: { entry: `src/${mode}.${mode === 'content' ? 'tsx' : 'ts'}`, name: 'FantasyGM', formats: ['iife'], fileName: () => `${mode}.js` } }
} : { build: { rollupOptions: { input: 'options.html' } } });
