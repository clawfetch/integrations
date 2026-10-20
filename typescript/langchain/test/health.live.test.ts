import { expect, it } from 'vitest';
import { createClawFetchClient } from '../src/index';

// Real network call to the FREE /health endpoint (no payment). Dummy key: never signs anything.
it('GET /health through the package client path', async () => {
  const client = createClawFetchClient({
    privateKey: '0x0000000000000000000000000000000000000000000000000000000000000001',
  });
  const health = await client.health();
  console.log('health:', JSON.stringify(health));
  expect(health).toBeTypeOf('object');
  expect(health.status).toBeDefined();
});
