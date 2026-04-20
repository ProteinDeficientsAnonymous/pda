import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

import { apiClient } from '@/api/client';
import { useRoles, useCreateRole, useUpdateRole, useDeleteRole } from './roles';

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedPatch = vi.mocked(apiClient.patch);
const mockedDelete = vi.mocked(apiClient.delete);

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function makeWrapper(qc: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useRoles', () => {
  it('returns a mapped list of roles on success', async () => {
    mockedGet.mockResolvedValueOnce({
      data: [
        { id: 'r1', name: 'member', is_default: true, permissions: [], user_count: 3 },
        { id: 'r2', name: 'admin', is_default: true, permissions: ['manage_users'], user_count: 1 },
      ],
    });

    const qc = makeQc();
    const { result } = renderHook(() => useRoles(), { wrapper: makeWrapper(qc) });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedGet).toHaveBeenCalledWith('/api/auth/roles/');
    expect(result.current.data).toEqual([
      { id: 'r1', name: 'member', isDefault: true, permissions: [], userCount: 3 },
      { id: 'r2', name: 'admin', isDefault: true, permissions: ['manage_users'], userCount: 1 },
    ]);
  });
});

describe('useCreateRole', () => {
  it('posts payload, maps response, and invalidates roles query', async () => {
    mockedPost.mockResolvedValueOnce({
      data: { id: 'r3', name: 'greeter', is_default: false, permissions: ['manage_events'] },
    });

    const qc = makeQc();
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useCreateRole(), { wrapper: makeWrapper(qc) });

    const role = await result.current.mutateAsync({
      name: 'greeter',
      permissions: ['manage_events'],
    });

    expect(mockedPost).toHaveBeenCalledWith('/api/auth/roles/', {
      name: 'greeter',
      permissions: ['manage_events'],
    });
    expect(role).toEqual({
      id: 'r3',
      name: 'greeter',
      isDefault: false,
      permissions: ['manage_events'],
      userCount: 0,
    });
    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['roles'] }));
  });
});

describe('useUpdateRole', () => {
  it('patches and invalidates both roles and users queries', async () => {
    mockedPatch.mockResolvedValueOnce({
      data: {
        id: 'r3',
        name: 'greeter',
        is_default: false,
        permissions: ['manage_events', 'approve_join_requests'],
      },
    });

    const qc = makeQc();
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useUpdateRole('r3'), { wrapper: makeWrapper(qc) });

    await result.current.mutateAsync({
      permissions: ['manage_events', 'approve_join_requests'],
    });

    expect(mockedPatch).toHaveBeenCalledWith('/api/auth/roles/r3/', {
      permissions: ['manage_events', 'approve_join_requests'],
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['roles'] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['users'] });
    });
  });
});

describe('useDeleteRole', () => {
  it('calls delete endpoint and invalidates roles query', async () => {
    mockedDelete.mockResolvedValueOnce({ data: undefined });

    const qc = makeQc();
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useDeleteRole(), { wrapper: makeWrapper(qc) });

    await result.current.mutateAsync('r3');

    expect(mockedDelete).toHaveBeenCalledWith('/api/auth/roles/r3/');
    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['roles'] }));
  });
});
