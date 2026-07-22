import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import { apiClient } from '@/api/client';

import { useVersion } from './version';

const mockedGet = vi.mocked(apiClient.get);

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useVersion', () => {
  it('returns the mapped version info', async () => {
    mockedGet.mockResolvedValueOnce({
      data: { commit_sha: 'abcdef123', commit_sha_short: 'abcdef1', environment: 'production' },
    });

    const { result } = renderHook(() => useVersion(), { wrapper: wrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual({
      commitSha: 'abcdef123',
      commitShaShort: 'abcdef1',
      environment: 'production',
    });
    expect(mockedGet).toHaveBeenCalledWith('/api/community/version/');
  });
});
