import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import { apiClient } from '@/api/client';
import { useJoinRequests, useSubmitJoinRequest, AlreadyInvitedError } from './join';

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

/** Create an axios-style error with a given HTTP status. */
function makeAxiosError(status: number, data: Record<string, unknown> = {}): Error {
  return Object.assign(new Error(`HTTP ${status}`), {
    isAxiosError: true,
    response: { status, data },
  });
}

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// useJoinRequests (admin list)
// ---------------------------------------------------------------------------

describe('useJoinRequests', () => {
  it('returns mapped list of join requests on success', async () => {
    mockedGet.mockResolvedValueOnce({
      data: [
        {
          id: 'jr-1',
          display_name: 'Alex Smith',
          phone_number: '+12125551234',
          answers: [{ question_id: 'q-1', label: 'Why join?', answer: 'Community' }],
          submitted_at: '2024-04-01T09:00:00Z',
          status: 'pending',
          user_id: null,
          previously_archived: false,
        },
      ],
    });

    const { result } = renderHook(() => useJoinRequests(), { wrapper: wrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([
      {
        id: 'jr-1',
        displayName: 'Alex Smith',
        phoneNumber: '+12125551234',
        answers: [{ questionId: 'q-1', label: 'Why join?', answer: 'Community' }],
        submittedAt: '2024-04-01T09:00:00Z',
        status: 'pending',
        userId: null,
        previouslyArchived: false,
        approvedAt: null,
        approvedByName: null,
        rejectedAt: null,
        rejectedByName: null,
        onboardedAt: null,
      },
    ]);

    expect(mockedGet).toHaveBeenCalledWith('/api/community/join-requests/');
  });

  it('surfaces a 403 error distinctly when the user lacks permission', async () => {
    const forbidden = makeAxiosError(403, { detail: 'Permission denied' });
    mockedGet.mockRejectedValueOnce(forbidden);

    const { result } = renderHook(() => useJoinRequests(), { wrapper: wrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));

    // The hook re-throws the raw axios error — callers inspect .response.status
    const err = result.current.error as { response?: { status?: number } };
    expect(err.response?.status).toBe(403);
  });

  it('re-throws other API errors unchanged', async () => {
    const serverError = makeAxiosError(500, { detail: 'Internal error' });
    mockedGet.mockRejectedValueOnce(serverError);

    const { result } = renderHook(() => useJoinRequests(), { wrapper: wrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));

    const err = result.current.error as { response?: { status?: number } };
    expect(err.response?.status).toBe(500);
  });
});

// ---------------------------------------------------------------------------
// useSubmitJoinRequest
// ---------------------------------------------------------------------------

const validPayload = {
  displayName: 'Sam Green',
  phoneNumber: '+12125559876',
  answers: { 'q-1': 'Because community', 'q-2': 'A friend' },
  smsConsent: true,
  website: '',
};

describe('useSubmitJoinRequest', () => {
  it('throws AlreadyInvitedError when server responds with 409', async () => {
    const conflict = makeAxiosError(409, { detail: 'already_invited' });
    mockedPost.mockRejectedValueOnce(conflict);

    const { result } = renderHook(() => useSubmitJoinRequest(), {
      wrapper: wrapper(),
    });

    await expect(result.current.mutateAsync(validPayload)).rejects.toBeInstanceOf(
      AlreadyInvitedError,
    );

    await waitFor(() => expect(result.current.error).toBeInstanceOf(AlreadyInvitedError));
    expect((result.current.error as AlreadyInvitedError).name).toBe('AlreadyInvitedError');
  });

  it('surfaces validation detail string when server responds with 400', async () => {
    const badRequest = makeAxiosError(400, {
      detail: 'A join request for this phone number is already pending.',
    });
    mockedPost.mockRejectedValueOnce(badRequest);

    const { result } = renderHook(() => useSubmitJoinRequest(), {
      wrapper: wrapper(),
    });

    await expect(result.current.mutateAsync(validPayload)).rejects.toMatchObject({
      response: { status: 400, data: { detail: expect.stringContaining('already pending') } },
    });
  });

  it('propagates network errors without wrapping', async () => {
    const networkError = new Error('Network Error');
    mockedPost.mockRejectedValueOnce(networkError);

    const { result } = renderHook(() => useSubmitJoinRequest(), {
      wrapper: wrapper(),
    });

    await expect(result.current.mutateAsync(validPayload)).rejects.toThrow('Network Error');
    expect(result.current.error).not.toBeInstanceOf(AlreadyInvitedError);
  });
});
