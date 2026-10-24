import { describe, expect, it, vi } from 'vitest';

import { reportError } from '@/utils/errorReporter';

import { queryClient } from './queryClient';

vi.mock('@/utils/errorReporter', () => ({ reportError: vi.fn() }));

async function failMutation(meta?: Record<string, unknown>) {
  await queryClient
    .getMutationCache()
    .build(queryClient, {
      mutationFn: () => Promise.reject(new Error('boom')),
      meta,
    })
    .execute(undefined)
    .catch(() => undefined);
}

describe('queryClient mutation error reporting', () => {
  it('reports failed mutations', async () => {
    await failMutation();
    expect(reportError).toHaveBeenCalledTimes(1);
  });

  it('skips reporting when meta.skipErrorReport is set', async () => {
    vi.mocked(reportError).mockClear();
    await failMutation({ skipErrorReport: true });
    expect(reportError).not.toHaveBeenCalled();
  });
});
