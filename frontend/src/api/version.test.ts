import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { queryWrapper } from '@/test/render';

import { useVersion } from './version';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const mockedGet = vi.mocked(apiClient.get);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useVersion', () => {
  it('returns the mapped version info', async () => {
    mockedGet.mockResolvedValueOnce({
      data: { commit_sha: 'abcdef123', commit_sha_short: 'abcdef1', environment: 'production' },
    });

    const { result } = renderHook(() => useVersion(), { wrapper: queryWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual({
      commitSha: 'abcdef123',
      commitShaShort: 'abcdef1',
      environment: 'production',
    });
    expect(mockedGet).toHaveBeenCalledWith('/api/community/version/');
  });
});
