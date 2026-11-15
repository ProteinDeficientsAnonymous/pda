import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { makeQueryClient, queryWrapper } from '@/test/render';

import { useCreateYear, usePropose, useWithdraw } from './planning';

vi.mock('@/api/client');

beforeEach(() => {
  vi.clearAllMocks();
});

function renderMutation<TVars>(useHook: () => { mutateAsync: (vars: TVars) => Promise<unknown> }) {
  const qc = makeQueryClient();
  const invalidate = vi.spyOn(qc, 'invalidateQueries');
  const { result } = renderHook(useHook, { wrapper: queryWrapper(qc) });
  return { run: (vars: TVars) => result.current.mutateAsync(vars), invalidate };
}

describe('planning mutations', () => {
  it('propose refreshes every planning query, my slots included', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: null });
    const { run, invalidate } = renderMutation(usePropose);
    await run({ slotId: 's1', userId: 'u1' });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['planning'] });
  });

  it('withdraw refreshes every planning query, even when the request fails', async () => {
    vi.mocked(apiClient.delete).mockRejectedValue(new Error('nope'));
    const { run, invalidate } = renderMutation(useWithdraw);
    await expect(run('a1')).rejects.toThrow('nope');
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['planning'] });
  });

  it('finishes invalidating before mutateAsync resolves', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: 'y', year: 2028 } });
    const { run, invalidate } = renderMutation(useCreateYear);
    let invalidated = false;
    invalidate.mockImplementation(async () => {
      await Promise.resolve();
      invalidated = true;
    });
    await run(2028);
    expect(invalidated).toBe(true);
  });
});
