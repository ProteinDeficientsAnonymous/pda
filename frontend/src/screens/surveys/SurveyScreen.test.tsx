import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { getStoredSurveyToken, setStoredSurveyToken } from '@/api/surveyTokenStorage';

import SurveyScreen from './SurveyScreen';
import SurveyThanksScreen from './SurveyThanksScreen';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), put: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

const toastError = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (m: string) => {
      toastError(m);
    },
  },
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

function makeQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderScreen(slug = 'feedback', qc = makeQueryClient()) {
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/surveys/${slug}`]}>
        <Routes>
          <Route path="/surveys/:slug" element={<SurveyScreen />} />
          <Route path="/surveys/:slug/thanks" element={<SurveyThanksScreen />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const baseWireSurvey = {
  id: 'srv-1',
  title: 'feedback survey',
  slug: 'feedback',
  visibility: 'public',
  is_active: true,
  questions: [
    { id: 'q1', label: 'thoughts', field_type: 'text', required: true, display_order: 0 },
  ],
  my_response_id: null,
  my_answers: null,
  poll_result: null,
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('SurveyScreen', () => {
  it('shows a required error and blocks submit when a required question is empty', async () => {
    const scroll = vi.spyOn(Element.prototype, 'scrollIntoView');
    mockedGet.mockResolvedValueOnce({ data: baseWireSurvey });
    renderScreen();

    fireEvent.click(await screen.findByRole('button', { name: 'submit' }));

    expect(await screen.findByText('required', { selector: 'p' })).toBeInTheDocument();
    expect(toastError).toHaveBeenCalledWith('answer the required questions before submitting');
    expect(scroll).toHaveBeenCalled();
    expect(mockedPost).not.toHaveBeenCalled();
  });

  it('submits answers for a first-time response', async () => {
    // success invalidates the survey query, so GET refetches — stub it to always resolve
    mockedGet.mockResolvedValue({ data: baseWireSurvey });
    mockedPost.mockResolvedValueOnce({
      data: {
        id: 'resp-1',
        user_id: null,
        user_name: null,
        answers: {},
        submitted_at: '2026-01-01T00:00:00Z',
      },
    });
    renderScreen();

    fireEvent.change(await screen.findByLabelText('thoughts · required'), {
      target: { value: 'great job' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'submit' }));

    await waitFor(() => {
      expect(mockedPost).toHaveBeenCalledWith(
        '/api/community/surveys/view/feedback/respond/',
        { answers: { q1: 'great job' } },
        { params: undefined },
      );
    });
    expect(await screen.findByText('thanks for filling out our survey!')).toBeInTheDocument();
  });

  it('labels the button "update response" and preloads the answer when already responded', async () => {
    mockedGet.mockResolvedValueOnce({
      data: {
        ...baseWireSurvey,
        my_response_id: 'resp-1',
        my_answers: { q1: { label: 'thoughts', answer: 'previous answer' } },
      },
    });
    renderScreen();

    expect(await screen.findByRole('button', { name: 'update response' })).toBeInTheDocument();
    expect(screen.getByLabelText('thoughts · required')).toHaveValue('previous answer');
  });

  it('renders a closed state instead of the form for an inactive survey', async () => {
    mockedGet.mockResolvedValueOnce({ data: { ...baseWireSurvey, is_active: false } });
    renderScreen();

    expect(await screen.findByRole('status')).toHaveTextContent('this survey is closed');
    expect(screen.getByRole('heading', { name: 'feedback survey' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /submit/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('thoughts · required')).not.toBeInTheDocument();
  });

  it('renders a scheduled state for a survey that has not opened yet', async () => {
    mockedGet.mockResolvedValueOnce({
      data: { ...baseWireSurvey, opens_at: '2999-01-01T00:00:00Z' },
    });
    renderScreen();

    expect(await screen.findByRole('status')).toHaveTextContent("this survey isn't open yet");
    expect(screen.queryByRole('button', { name: /submit/ })).not.toBeInTheDocument();
  });

  it('renders a capped state for a survey at its response limit', async () => {
    mockedGet.mockResolvedValueOnce({
      data: { ...baseWireSurvey, max_responses: 2, response_count: 2 },
    });
    renderScreen();

    expect(await screen.findByRole('status')).toHaveTextContent('reached its response limit');
    expect(screen.queryByRole('button', { name: /submit/ })).not.toBeInTheDocument();
  });

  it('still lets a user past the cap edit their own response', async () => {
    mockedGet.mockResolvedValueOnce({
      data: {
        ...baseWireSurvey,
        max_responses: 2,
        response_count: 2,
        my_response_id: 'resp-1',
        my_answers: { q1: { label: 'thoughts', answer: 'previous answer' } },
      },
    });
    renderScreen();

    expect(await screen.findByRole('button', { name: 'update response' })).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('renders the form with a submit button for an active survey', async () => {
    mockedGet.mockResolvedValueOnce({ data: baseWireSurvey });
    renderScreen();

    expect(await screen.findByRole('button', { name: 'submit' })).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('keeps the finalized-poll view for an inactive survey with a poll result', async () => {
    mockedGet.mockResolvedValueOnce({
      data: {
        ...baseWireSurvey,
        is_active: false,
        poll_result: {
          id: 'r1',
          winning_datetime: '2030-01-01T10:00:00Z',
          finalized_by_id: null,
          finalized_at: '2029-12-01T10:00:00Z',
        },
      },
    });
    renderScreen();

    expect(await screen.findByText(/this poll has been finalized/)).toBeInTheDocument();
    expect(screen.queryByText(/this survey is closed/)).not.toBeInTheDocument();
  });

  it('refetches the survey when a submit is rejected because it closed', async () => {
    mockedGet.mockResolvedValue({ data: baseWireSurvey });
    mockedPost.mockRejectedValueOnce({
      isAxiosError: true,
      response: { status: 400, data: { detail: [{ code: 'survey.closed' }] } },
    });

    const qc = makeQueryClient();
    const invalidate = vi.spyOn(qc, 'invalidateQueries');
    renderScreen('feedback', qc);

    fireEvent.change(await screen.findByLabelText('thoughts · required'), {
      target: { value: 'too late' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'submit' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('this survey is closed');
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['survey', 'feedback'] });
  });
});

describe('SurveyScreen post-submit confirmation', () => {
  async function submitWith(confirmationMessage: string) {
    mockedGet.mockResolvedValue({
      data: { ...baseWireSurvey, confirmation_message: confirmationMessage },
    });
    mockedPost.mockResolvedValueOnce({
      data: {
        id: 'resp-1',
        user_id: null,
        user_name: null,
        answers: {},
        submitted_at: '2026-01-01T00:00:00Z',
      },
    });
    renderScreen();
    fireEvent.change(await screen.findByLabelText('thoughts · required'), {
      target: { value: 'great job' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'submit' }));
  }

  it('redirects to the thank-you page with the custom message, lowercased', async () => {
    await submitWith('Thanks For Your Feedback!');
    expect(
      await screen.findByRole('heading', { name: 'thanks for your feedback!' }),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'submit' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'edit your response' })).toHaveAttribute(
      'href',
      '/surveys/feedback',
    );
  });

  it('falls back to the default thank-you message when none is set', async () => {
    await submitWith('   ');
    expect(
      await screen.findByRole('heading', { name: 'thanks for filling out our survey!' }),
    ).toBeInTheDocument();
  });

  it('still shows the thank-you page when the submit fills the response cap', async () => {
    mockedGet
      .mockResolvedValueOnce({
        data: { ...baseWireSurvey, confirmation_message: 'thanks!', max_responses: 1 },
      })
      .mockResolvedValue({
        data: {
          ...baseWireSurvey,
          confirmation_message: 'thanks!',
          max_responses: 1,
          response_count: 1,
        },
      });
    mockedPost.mockResolvedValueOnce({
      data: { id: 'r', user_id: null, user_name: null, answers: {}, submitted_at: '' },
    });
    renderScreen();
    fireEvent.change(await screen.findByLabelText('thoughts · required'), {
      target: { value: 'hi' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'submit' }));

    expect(await screen.findByRole('heading', { name: 'thanks!' })).toBeInTheDocument();
    expect(screen.queryByText(/reached its response limit/)).not.toBeInTheDocument();
  });

  it('tells participants an anonymous survey is anonymous', async () => {
    mockedGet.mockResolvedValueOnce({ data: { ...baseWireSurvey, anonymous: true } });
    renderScreen();
    expect(await screen.findByText(/responses are anonymous/)).toBeInTheDocument();
  });

  it('does not show the confirmation message before submitting', async () => {
    mockedGet.mockResolvedValueOnce({
      data: { ...baseWireSurvey, confirmation_message: 'thanks!' },
    });
    renderScreen();
    await screen.findByRole('button', { name: 'submit' });
    expect(screen.queryByText('thanks!')).not.toBeInTheDocument();
  });
});

describe('SurveyScreen anonymous response token', () => {
  const respondedSurvey = {
    ...baseWireSurvey,
    one_response_per_user: true,
    my_response_id: 'resp-1',
    my_answers: { q1: { label: 'thoughts', answer: 'previous answer' } },
  };

  beforeEach(() => {
    localStorage.clear();
  });

  it('sends the stored token when loading and submitting', async () => {
    setStoredSurveyToken('feedback', 'tok-1');
    mockedGet.mockResolvedValue({ data: respondedSurvey });
    mockedPost.mockResolvedValueOnce({
      data: {
        id: 'resp-1',
        user_id: null,
        user_name: null,
        answers: {},
        submitted_at: '2026-01-01T00:00:00Z',
        response_token: 'tok-1',
      },
    });
    renderScreen();

    fireEvent.click(await screen.findByRole('button', { name: 'update response' }));

    await waitFor(() => {
      expect(mockedPost).toHaveBeenCalledWith(
        '/api/community/surveys/view/feedback/respond/',
        { answers: { q1: 'previous answer' } },
        { params: { response_token: 'tok-1' } },
      );
    });
    expect(mockedGet).toHaveBeenCalledWith('/api/community/surveys/view/feedback/', {
      params: { response_token: 'tok-1' },
    });
  });

  it('stores a token returned by the submit', async () => {
    mockedGet.mockResolvedValue({ data: { ...baseWireSurvey, one_response_per_user: true } });
    mockedPost.mockResolvedValueOnce({
      data: {
        id: 'resp-1',
        user_id: null,
        user_name: null,
        answers: {},
        submitted_at: '2026-01-01T00:00:00Z',
        response_token: 'fresh-token',
      },
    });
    renderScreen();

    fireEvent.change(await screen.findByLabelText('thoughts · required'), {
      target: { value: 'hi' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'submit' }));

    await waitFor(() => {
      expect(getStoredSurveyToken('feedback')).toBe('fresh-token');
    });
  });

  it('lets a visitor drop the stored token and start a new response', async () => {
    setStoredSurveyToken('feedback', 'tok-1');
    mockedGet.mockResolvedValueOnce({ data: respondedSurvey });
    mockedGet.mockResolvedValue({ data: { ...baseWireSurvey, one_response_per_user: true } });
    renderScreen();

    fireEvent.click(await screen.findByRole('button', { name: 'not you? start a new response' }));

    expect(getStoredSurveyToken('feedback')).toBeNull();
    expect(screen.getByLabelText('thoughts · required')).toHaveValue('');
    expect(await screen.findByRole('button', { name: 'submit' })).toBeInTheDocument();
  });

  it('hides the start-fresh action without a stored token', async () => {
    mockedGet.mockResolvedValueOnce({ data: respondedSurvey });
    renderScreen();

    expect(await screen.findByRole('button', { name: 'update response' })).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'not you? start a new response' }),
    ).not.toBeInTheDocument();
  });
});
