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
import { useSurveyPollTallies, useFinalizeSurveyPoll } from './surveyAdmin';

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

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

describe('useSurveyPollTallies', () => {
  it('should map tally rows and voters', async () => {
    mockedGet.mockResolvedValueOnce({
      data: [
        {
          question_id: 'q1',
          tallies: { '2026-04-20T12:00:00.000Z': { yes: 2, maybe: 1 } },
          voters: {
            '2026-04-20T12:00:00.000Z': [
              { user_id: 'u1', name: 'ada', photo_url: '' },
            ],
          },
          total_responses: 3,
        },
      ],
    });
    const qc = makeQc();
    const { result } = renderHook(() => useSurveyPollTallies('srv-1'), {
      wrapper: makeWrapper(qc),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedGet).toHaveBeenCalledWith('/api/community/surveys/srv-1/tallies/');
    const row = result.current.data![0]!;
    expect(row.questionId).toBe('q1');
    expect(row.tallies['2026-04-20T12:00:00.000Z']).toEqual({ yes: 2, maybe: 1 });
    expect(row.voters['2026-04-20T12:00:00.000Z']![0]).toEqual({
      userId: 'u1',
      name: 'ada',
      photoUrl: '',
    });
    expect(row.totalResponses).toBe(3);
  });
});

describe('useFinalizeSurveyPoll', () => {
  it('should post winning datetime and refresh survey cache', async () => {
    const wireSurvey = {
      id: 'srv-1',
      title: 't',
      slug: 's',
      visibility: 'members_only',
      is_active: false,
      questions: [],
      poll_result: {
        id: 'pr1',
        winning_datetime: '2026-04-20T12:00:00.000Z',
        finalized_by_id: 'u-me',
        finalized_at: '2026-04-20T13:00:00.000Z',
      },
    };
    mockedPost.mockResolvedValueOnce({ data: wireSurvey });
    const qc = makeQc();
    const { result } = renderHook(() => useFinalizeSurveyPoll('srv-1'), {
      wrapper: makeWrapper(qc),
    });
    const dt = new Date('2026-04-20T12:00:00.000Z');
    await result.current.mutateAsync(dt);
    expect(mockedPost).toHaveBeenCalledWith('/api/community/surveys/srv-1/finalize/', {
      winning_datetime: dt.toISOString(),
    });
    await waitFor(() => {
      expect(qc.getQueryData(['surveys', 'admin', 'srv-1'])!).toEqual(
        expect.objectContaining({
          pollResult: expect.objectContaining({ id: 'pr1' }),
        }),
      );
    });
  });
});
