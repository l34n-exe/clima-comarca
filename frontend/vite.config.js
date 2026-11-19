import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// En desarrollo, /api se reenvía a Flask para evitar problemas de CORS
const target = process.env.API_PROXY || 'http://localhost:5000';

export default defineConfig({
  plugins: [svelte()],
  server: { host: true, port: 5173, proxy: { '/api': target } },
});
