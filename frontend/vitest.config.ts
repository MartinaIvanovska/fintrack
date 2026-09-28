/// <reference types="vitest" />
// Component tests for the React app (Vitest + React Testing Library + MSW).
// Tests live in tests/ - outside src/ - so the Create React App build and its
// type check are unaffected. Run with `npm test` or `npm run test:coverage`.
import { defineConfig } from 'vitest/config';

export default defineConfig({
  esbuild: { jsx: 'automatic' }, // React 17+ JSX runtime
  test: {
    environment: 'jsdom',
    environmentOptions: { jsdom: { url: 'http://localhost:3000/' } },
    include: ['tests/**/*.test.{ts,tsx}'],
    setupFiles: ['tests/setup.ts'],
    restoreMocks: true,
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/index.tsx', 'src/reportWebVitals.ts', 'src/react-app-env.d.ts', 'src/types/**'],
      reporter: ['text', 'html', 'lcov'],
      reportsDirectory: 'coverage',
      // Coverage gate: `npm run test:coverage` fails below these
      thresholds: {
        statements: 100,
        lines: 100,
        branches: 95,
        functions: 75,
      },
    },
  },
});
