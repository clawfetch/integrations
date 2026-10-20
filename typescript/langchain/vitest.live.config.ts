import { defineConfig } from 'vitest/config';

// Real network calls to free endpoints only. Run with `npm run test:live`.
export default defineConfig({
  test: { include: ['test/**/*.live.test.ts'] },
});
