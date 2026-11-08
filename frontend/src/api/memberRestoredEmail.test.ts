import { QueryClient } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { queryWrapper } from '@/test/render';

import { useMemberRestoredEmail, useUpdateMemberRestoredEmail } from './memberRestoredEmail';

vi.mock('@/api/client');

vi.mock('@/auth/store', () => ({
  useAuthStore: vi.fn((selector: (s: { status: string }) => unknown) =>
    selector({ status: 'authed' }),
  ),
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPatch = vi.mocked(apiClient.patch);

const URL = '/api/community/member-restored-email/';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useMemberRestoredEmail', () => {
  it('returns the mapped template', async () => {
    mockedGet.mockResolvedValueOnce({
      data: { body: 'welcome back!', updated_at: '2026-11-01T00:00:00Z' },
    });

    const { result } = renderHook(() => useMemberRestoredEmail(), { wrapper: queryWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({
      body: 'welcome back!',
      updatedAt: '2026-11-01T00:00:00Z',
    });
    expect(mockedGet).toHaveBeenCalledWith(URL);
  });
});

describe('useUpdateMemberRestoredEmail', () => {
  it('patches the body and caches the saved template', async () => {
    mockedPatch.mockResolvedValueOnce({
      data: { body: 'new body', updated_at: '2026-11-02T00:00:00Z' },
    });
    const qc = new QueryClient();

    const { result } = renderHook(() => useUpdateMemberRestoredEmail(), {
      wrapper: queryWrapper(qc),
    });

    await act(() => result.current.mutateAsync('new body'));

    expect(mockedPatch).toHaveBeenCalledWith(URL, { body: 'new body' });
    expect(qc.getQueryData(['member-restored-email'])).toEqual({
      body: 'new body',
      updatedAt: '2026-11-02T00:00:00Z',
    });
  });
});
