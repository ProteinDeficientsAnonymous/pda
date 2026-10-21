import { afterAll, vi } from 'vitest';

// isolate: false shares one environment and module cache per worker. Restore
// globals before Vitest loads the next file (it calls `new URL` while loading),
// then drop modules imported under the previous file's vi.mock.
afterAll(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.useRealTimers();
});

vi.resetModules();
