import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { QuestionType } from '@/api/questionTypes';
import { makeQueryClient, queryWrapper } from '@/test/render';

import { useSurveyPollTallies, useSurveyQuestionSummaries } from './surveyAdmin';

vi.mock('@/api/client');

const mockedGet = vi.mocked(apiClient.get);

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
            '2026-04-20T12:00:00.000Z': [{ user_id: 'u1', name: 'ada', photo_url: '' }],
          },
          total_responses: 3,
        },
      ],
    });
    const qc = makeQueryClient();
    const { result } = renderHook(() => useSurveyPollTallies('srv-1'), {
      wrapper: queryWrapper(qc),
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

describe('useSurveyQuestionSummaries', () => {
  it('should pass the event filter as event_id', async () => {
    mockedGet.mockResolvedValueOnce({ data: [] });
    const qc = makeQueryClient();
    const { result } = renderHook(() => useSurveyQuestionSummaries('srv-1', 'ev-1'), {
      wrapper: queryWrapper(qc),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedGet).toHaveBeenCalledWith('/api/community/surveys/srv-1/summary/', {
      params: { event_id: 'ev-1' },
    });
  });

  it('should map wire summary rows', async () => {
    mockedGet.mockResolvedValueOnce({
      data: [
        {
          question_id: 'q1',
          field_type: QuestionType.Stars,
          counts: { '1': 0, '2': 1, '3': 0, '4': 0, '5': 1 },
          answered: 2,
          mean: 3.5,
        },
        { question_id: 'q2', field_type: 'radio', counts: { red: 1 }, answered: 1 },
      ],
    });
    const qc = makeQueryClient();
    const { result } = renderHook(() => useSurveyQuestionSummaries('srv-1'), {
      wrapper: queryWrapper(qc),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedGet).toHaveBeenCalledWith('/api/community/surveys/srv-1/summary/', {
      params: undefined,
    });
    const [rating, radio] = result.current.data!;
    expect(rating).toEqual({
      questionId: 'q1',
      fieldType: QuestionType.Stars,
      counts: { '1': 0, '2': 1, '3': 0, '4': 0, '5': 1 },
      answered: 2,
      mean: 3.5,
    });
    expect(radio!.mean).toBeNull();
  });

  it('should not fetch without a survey id', () => {
    const qc = makeQueryClient();
    renderHook(() => useSurveyQuestionSummaries(undefined), { wrapper: queryWrapper(qc) });
    expect(mockedGet).not.toHaveBeenCalled();
  });
});
