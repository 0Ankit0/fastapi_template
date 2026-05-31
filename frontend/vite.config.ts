import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const internalApiBaseUrl = env.INTERNAL_API_BASE_URL ?? 'http://localhost:8000';

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    define: {
      'process.env': JSON.stringify(env),
    },
    server: {
      host: '0.0.0.0',
      port: 3000,
      proxy: {
        '/api/v1': {
          target: internalApiBaseUrl,
          changeOrigin: true,
        },
      },
    },
    preview: {
      host: '0.0.0.0',
      port: 3000,
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) {
              return;
            }

            if (id.includes('firebase')) {
              return 'vendor-firebase';
            }

            if (id.includes('posthog-js') || id.includes('mixpanel-browser')) {
              return 'vendor-analytics';
            }

            if (id.includes('react-router-dom') || id.includes('@tanstack/react-query')) {
              return 'vendor-routing-data';
            }

            if (id.includes('react') || id.includes('scheduler')) {
              return 'vendor-react';
            }
          },
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    },
  };
});