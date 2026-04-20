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
import {
  useUsers,
  useCreateUser,
  useUpdateUser,
  useBulkCreateUsers,
  useArchiveUser,
  useSendMemberMagicLink,
  useUpdateMemberRoles,
} from './users';

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedPatch = vi.mocked(apiClient.patch);
const mockedDelete = vi.mocked(apiClient.delete);

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

// Each hook gets a fresh QueryClient so invalidations are observable in isolation.
function makeWrapper(qc: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// useUsers
// ---------------------------------------------------------------------------

describe('useUsers', () => {
  it('returns a mapped list of members on success', async () => {
    mockedGet.mockResolvedValueOnce({
      data: [
        {
          id: 'u1',
          display_name: 'Ada',
          phone_number: '+15551230001',
          email: 'ada@example.com',
          bio: '',
          profile_photo_url: '',
          show_phone: true,
          show_email: false,
          is_superuser: false,
          is_paused: false,
          needs_onboarding: false,
          login_link_requested: false,
          roles: [
            {
              id: 'r1',
              name: 'member',
              is_default: true,
              permissions: [],
            },
          ],
        },
      ],
    });

    const qc = makeQc();
    const { result } = renderHook(() => useUsers(), { wrapper: makeWrapper(qc) });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedGet).toHaveBeenCalledWith('/api/auth/users/');
    expect(result.current.data).toHaveLength(1);
    const [member] = result.current.data!;
    expect(member?.displayName).toBe('Ada');
    expect(member?.phoneNumber).toBe('+15551230001');
    expect(member?.email).toBe('ada@example.com');
    expect(member?.showPhone).toBe(true);
    expect(member?.showEmail).toBe(false);
    expect(member?.roles[0]).toEqual({
      id: 'r1',
      name: 'member',
      isDefault: true,
      permissions: [],
    });
  });

  it('propagates errors from the API', async () => {
    const apiError = new Error('network down');
    mockedGet.mockRejectedValueOnce(apiError);

    const qc = makeQc();
    const { result } = renderHook(() => useUsers(), { wrapper: makeWrapper(qc) });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(apiError);
  });

  // TODO(tier3-mismatch): Flutter `useUsers returns 403 distinctly` — React
  // `useUsers` does not special-case 403 responses (no error branch in the
  // queryFn), so there's nothing distinct to assert. Route-level guards
  // handle permission gating instead.
  it.skip('surfaces 403 distinctly from other errors', () => {
    // Intentionally empty — mismatch vs Flutter behavior, documented above.
  });
});

// ---------------------------------------------------------------------------
// useCreateUser
// ---------------------------------------------------------------------------

describe('useCreateUser', () => {
  it('posts the payload, maps the response, and invalidates the users query', async () => {
    mockedPost.mockResolvedValueOnce({
      data: {
        id: 'u2',
        phone_number: '+15551230002',
        display_name: 'Grace',
        magic_link_token: 'magic-abc',
      },
    });

    const qc = makeQc();
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useCreateUser(), { wrapper: makeWrapper(qc) });

    const created = await result.current.mutateAsync({
      phoneNumber: '+15551230002',
      displayName: 'Grace',
      email: 'grace@example.com',
      roleId: 'role-xyz',
    });

    expect(mockedPost).toHaveBeenCalledWith('/api/auth/create-user/', {
      phone_number: '+15551230002',
      display_name: 'Grace',
      email: 'grace@example.com',
      role_id: 'role-xyz',
    });
    expect(created).toEqual({
      id: 'u2',
      phoneNumber: '+15551230002',
      displayName: 'Grace',
      magicLinkToken: 'magic-abc',
    });
    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['users'] }));
  });

  it('omits optional fields from the wire payload when not provided', async () => {
    mockedPost.mockResolvedValueOnce({
      data: {
        id: 'u3',
        phone_number: '+15551230003',
        display_name: '',
        magic_link_token: 'magic-xyz',
      },
    });

    const qc = makeQc();
    const { result } = renderHook(() => useCreateUser(), { wrapper: makeWrapper(qc) });

    await result.current.mutateAsync({ phoneNumber: '+15551230003' });

    expect(mockedPost).toHaveBeenCalledWith('/api/auth/create-user/', {
      phone_number: '+15551230003',
    });
  });
});

// ---------------------------------------------------------------------------
// useUpdateUser — not on the Flutter list, but it's the natural pair for
// useCreateUser and the test doc for tier 3 implicitly covers the admin CRUD
// surface. Keep lightweight: one happy-path assertion.
// ---------------------------------------------------------------------------

describe('useUpdateUser', () => {
  it('patches the user and invalidates the users query', async () => {
    mockedPatch.mockResolvedValueOnce({
      data: {
        id: 'u1',
        display_name: 'Ada Lovelace',
        phone_number: '+15551230001',
        roles: [],
      },
    });

    const qc = makeQc();
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useUpdateUser('u1'), { wrapper: makeWrapper(qc) });

    await result.current.mutateAsync({ displayName: 'Ada Lovelace', isPaused: false });

    expect(mockedPatch).toHaveBeenCalledWith('/api/auth/users/u1/', {
      display_name: 'Ada Lovelace',
      is_paused: false,
    });
    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['users'] }));
  });
});

describe('useBulkCreateUsers', () => {
  it('posts the phone list, maps results, and invalidates users query', async () => {
    mockedPost.mockResolvedValueOnce({
      data: {
        results: [
          {
            row: 1,
            phone_number: '+15551230001',
            success: true,
            magic_link_token: 'magic-1',
          },
          {
            row: 2,
            phone_number: 'garbage',
            success: false,
            error: 'Invalid phone number',
          },
        ],
        created: 1,
        failed: 1,
      },
    });

    const qc = makeQc();
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useBulkCreateUsers(), { wrapper: makeWrapper(qc) });

    const response = await result.current.mutateAsync(['+15551230001', 'garbage']);

    expect(mockedPost).toHaveBeenCalledWith('/api/auth/bulk-create-users/', {
      phone_numbers: ['+15551230001', 'garbage'],
    });
    expect(response.created).toBe(1);
    expect(response.failed).toBe(1);
    expect(response.results[0]).toEqual({
      row: 1,
      phoneNumber: '+15551230001',
      success: true,
      error: undefined,
      magicLinkToken: 'magic-1',
    });
    expect(response.results[1]?.success).toBe(false);
    expect(response.results[1]?.error).toBe('Invalid phone number');
    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['users'] }));
  });
});

describe('useArchiveUser', () => {
  it('calls delete endpoint and invalidates users query', async () => {
    mockedDelete.mockResolvedValueOnce({ data: undefined });

    const qc = makeQc();
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useArchiveUser(), { wrapper: makeWrapper(qc) });

    await result.current.mutateAsync('u-archive');

    expect(mockedDelete).toHaveBeenCalledWith('/api/auth/users/u-archive/');
    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['users'] }));
  });
});

describe('useSendMemberMagicLink', () => {
  it('posts magic-link and maps token', async () => {
    mockedPost.mockResolvedValueOnce({
      data: { detail: 'Magic login link generated.', magic_link_token: 'tok-abc' },
    });
    const qc = makeQc();
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useSendMemberMagicLink('u9'), { wrapper: makeWrapper(qc) });
    const out = await result.current.mutateAsync();
    expect(mockedPost).toHaveBeenCalledWith('/api/auth/users/u9/magic-link/');
    expect(out.magicLinkToken).toBe('tok-abc');
    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['users'] }));
  });
});

describe('useUpdateMemberRoles', () => {
  it('patches role_ids and maps member', async () => {
    mockedPatch.mockResolvedValueOnce({
      data: {
        id: 'u9',
        display_name: 'Ada',
        phone_number: '+1',
        roles: [
          { id: 'r2', name: 'vet', is_default: false, permissions: ['approve_join_requests'] },
        ],
      },
    });
    const qc = makeQc();
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useUpdateMemberRoles('u9'), { wrapper: makeWrapper(qc) });
    const member = await result.current.mutateAsync(['r2']);
    expect(mockedPatch).toHaveBeenCalledWith('/api/auth/users/u9/roles/', { role_ids: ['r2'] });
    expect(member.roles[0]?.name).toBe('vet');
    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['users'] }));
  });
});
