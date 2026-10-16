import { afterEach, describe, expect, it, vi } from 'vitest';

import { preloadOnPath } from './lazyRoute';

afterEach(() => {
  window.history.pushState({}, '', '/');
});

describe('preloadOnPath', () => {
  it('starts the chunk download when landing on the path', () => {
    window.history.pushState({}, '', '/Calendar?view=month');
    const factory = vi.fn(() => Promise.resolve({}));

    preloadOnPath('/calendar', factory);

    expect(factory).toHaveBeenCalledOnce();
  });

  it('does nothing on other paths', () => {
    window.history.pushState({}, '', '/events/abc');
    const factory = vi.fn(() => Promise.resolve({}));

    preloadOnPath('/calendar', factory);

    expect(factory).not.toHaveBeenCalled();
  });

  it('swallows a failed preload so the route can retry on render', async () => {
    window.history.pushState({}, '', '/calendar');
    const factory = vi.fn(() => Promise.reject(new Error('failed to fetch')));

    // Vitest fails the run on an unhandled rejection.
    preloadOnPath('/calendar', factory);
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(factory).toHaveBeenCalledOnce();
  });
});
