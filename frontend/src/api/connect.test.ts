import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';

import { useApproveConnect, useConnectRequest, useDenyConnect } from './connect';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('connect api', () => {
  it('fetches a connect request and maps to camelCase', async () => {
    mockedGet.mockResolvedValueOnce({
      data: {
        client_name: 'claude',
        redirect_host: 'claude.ai',
        expires_at: '2026-10-01T12:10:00Z',
      },
    });
    const { result } = renderHook(() => useConnectRequest('r1'), { wrapper: wrapper() });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(mockedGet).toHaveBeenCalledWith('/api/connect/requests/r1/');
    expect(result.current.data).toEqual({
      clientName: 'claude',
      redirectHost: 'claude.ai',
      expiresAt: new Date('2026-10-01T12:10:00Z'),
    });
  });

  it('does not fetch without a request id', () => {
    renderHook(() => useConnectRequest(null), { wrapper: wrapper() });
    expect(mockedGet).not.toHaveBeenCalled();
  });

  it('posts approve and deny and returns the redirect url', async () => {
    mockedPost.mockResolvedValue({ data: { redirect_url: 'https://claude.ai/cb?code=x' } });
    const { result } = renderHook(() => ({ a: useApproveConnect(), d: useDenyConnect() }), {
      wrapper: wrapper(),
    });
    await expect(result.current.a.mutateAsync('r1')).resolves.toBe('https://claude.ai/cb?code=x');
    await expect(result.current.d.mutateAsync('r2')).resolves.toBe('https://claude.ai/cb?code=x');
    expect(mockedPost).toHaveBeenNthCalledWith(1, '/api/connect/requests/r1/approve/');
    expect(mockedPost).toHaveBeenNthCalledWith(2, '/api/connect/requests/r2/deny/');
  });
});
