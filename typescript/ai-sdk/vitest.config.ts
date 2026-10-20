import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // *.live.test.ts makes real (free) network calls; run via `npm run test:live`.
    exclude: ['**/node_modules/**', '**/dist/**', '**/*.live.test.ts'],
  },
});
