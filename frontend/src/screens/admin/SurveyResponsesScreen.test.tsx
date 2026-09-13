import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type * as ReactRouterDom from 'react-router-dom';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Survey, SurveyResponseAdmin } from '@/api/surveyAdmin';
import {
  useAdminSurvey,
  useDeleteSurveyResponse,
  useFinalizeSurveyPoll,
  useSurveyPollTallies,
  useSurveyResponses,
} from '@/api/surveyAdmin';

import SurveyResponsesScreen from './SurveyResponsesScreen';

vi.mock('@/api/surveyAdmin', () => ({
  useAdminSurvey: vi.fn(),
  useSurveyResponses: vi.fn(),
  useSurveyPollTallies: vi.fn(),
  useFinalizeSurveyPoll: vi.fn(),
  useDeleteSurveyResponse: vi.fn(),
}));

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof ReactRouterDom>();
  return { ...actual, useParams: () => ({ id: 'survey-1' }) };
});

const mockUseAdminSurvey = vi.mocked(useAdminSurvey);
const mockUseSurveyResponses = vi.mocked(useSurveyResponses);
const mockUseSurveyPollTallies = vi.mocked(useSurveyPollTallies);
const mockUseFinalizeSurveyPoll = vi.mocked(useFinalizeSurveyPoll);
const mockUseDeleteSurveyResponse = vi.mocked(useDeleteSurveyResponse);

const deleteMutate = vi.fn();

function makeSurvey(overrides: Partial<Survey> = {}): Survey {
  return {
    id: 'survey-1',
    title: 'Feedback survey',
    description: '',
    slug: 'feedback',
    visibility: 'members_only',
    isActive: true,
    oneResponsePerUser: false,
    anonymous: false,
    confirmationMessage: '',
    questions: [
      {
        id: 'q1',
        label: 'Thoughts?',
        fieldType: 'text',
        options: [],
        required: false,
        displayOrder: 0,
      },
    ],
    myResponseId: null,
    myAnswers: null,
    pollResult: null,
    ...overrides,
  };
}

function makeResponse(overrides: Partial<SurveyResponseAdmin> = {}): SurveyResponseAdmin {
  return {
    id: 'r1',
    userId: 'u1',
    userName: 'Ada Lovelace',
    answers: { q1: { answer: 'great' } },
    submittedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  deleteMutate.mockReset();
  mockUseAdminSurvey.mockReturnValue({
    data: makeSurvey(),
    isPending: false,
    isError: false,
    isSuccess: true,
  } as unknown as ReturnType<typeof useAdminSurvey>);
  mockUseSurveyPollTallies.mockReturnValue({
    data: [],
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof useSurveyPollTallies>);
  mockUseFinalizeSurveyPoll.mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useFinalizeSurveyPoll>);
  mockUseDeleteSurveyResponse.mockReturnValue({
    mutate: deleteMutate,
    isPending: false,
  } as unknown as ReturnType<typeof useDeleteSurveyResponse>);
});

function mockResponses(responses: SurveyResponseAdmin[]) {
  mockUseSurveyResponses.mockReturnValue({
    data: responses,
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof useSurveyResponses>);
}

function renderScreen() {
  return render(
    <MemoryRouter>
      <SurveyResponsesScreen />
    </MemoryRouter>,
  );
}

describe('SurveyResponsesScreen delete action', () => {
  it('deletes a response when confirmed', async () => {
    mockResponses([makeResponse()]);
    const user = userEvent.setup();
    renderScreen();

    await user.click(screen.getByRole('button', { name: 'delete' }));
    const dialog = screen.getByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'delete' }));

    expect(deleteMutate).toHaveBeenCalledWith('r1');
  });

  it('does not delete a response when cancelled', async () => {
    mockResponses([makeResponse()]);
    const user = userEvent.setup();
    renderScreen();

    await user.click(screen.getByRole('button', { name: 'delete' }));
    await user.click(screen.getByRole('button', { name: 'cancel' }));

    expect(deleteMutate).not.toHaveBeenCalled();
  });
});
