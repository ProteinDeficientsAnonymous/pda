import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';

import {
  useApproveConnect,
  useConnectedApps,
  useConnectRequest,
  useDenyConnect,
  useMemberConnectedApps,
  useRevokeConnectedApp,
  useRevokeMemberConnectedApp,
} from './connect';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedDelete = vi.mocked(apiClient.delete);

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children);
}

const WIRE_APP = {
  id: 'g1',
  client_name: 'claude',
  created_at: '2026-10-01T12:00:00Z',
  last_used_at: null,
};

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

  it('lists my connected apps', async () => {
    mockedGet.mockResolvedValueOnce({ data: [WIRE_APP] });
    const { result } = renderHook(() => useConnectedApps(), { wrapper: wrapper() });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(mockedGet).toHaveBeenCalledWith('/api/connect/apps/');
    expect(result.current.data).toEqual([
      {
        id: 'g1',
        clientName: 'claude',
        createdAt: new Date('2026-10-01T12:00:00Z'),
        lastUsedAt: null,
      },
    ]);
  });

  it('revokes my connected app', async () => {
    mockedDelete.mockResolvedValueOnce({ data: undefined });
    const { result } = renderHook(() => useRevokeConnectedApp(), { wrapper: wrapper() });
    await result.current.mutateAsync('g1');
    expect(mockedDelete).toHaveBeenCalledWith('/api/connect/apps/g1/');
  });

  it('lists and revokes a member connected app as admin', async () => {
    mockedGet.mockResolvedValueOnce({
      data: [{ ...WIRE_APP, last_used_at: '2026-10-02T00:00:00Z' }],
    });
    mockedDelete.mockResolvedValueOnce({ data: undefined });
    const { result } = renderHook(
      () => ({ list: useMemberConnectedApps('u1'), revoke: useRevokeMemberConnectedApp('u1') }),
      { wrapper: wrapper() },
    );
    await waitFor(() => {
      expect(result.current.list.isSuccess).toBe(true);
    });
    expect(mockedGet).toHaveBeenCalledWith('/api/connect/users/u1/apps/');
    expect(result.current.list.data?.[0]?.lastUsedAt).toEqual(new Date('2026-10-02T00:00:00Z'));
    await result.current.revoke.mutateAsync('g1');
    expect(mockedDelete).toHaveBeenCalledWith('/api/connect/users/u1/apps/g1/');
  });
});
