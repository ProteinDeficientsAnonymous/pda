import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { authClient } from '@/api/client';

import FeedbackScreen from './FeedbackScreen';

vi.mock('@/api/client', () => ({
  authClient: { get: vi.fn(), post: vi.fn() },
}));

const mockedGet = vi.mocked(authClient.get);
const mockedPost = vi.mocked(authClient.post);

function renderScreen(entry = '/feedback#tok-1') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[entry]}>
        <Routes>
          <Route path="/feedback" element={<FeedbackScreen />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const wireSurvey = {
  id: 'srv-1',
  title: 'event feedback',
  slug: 'event-feedback',
  visibility: 'public',
  is_active: true,
  confirmation_message: '',
  questions: [
    { id: 'q1', label: 'thoughts', field_type: 'text', required: true, display_order: 0 },
  ],
};

function wireFeedback(overrides: Record<string, unknown> = {}) {
  return {
    data: {
      survey: wireSurvey,
      event_id: 'evt-1',
      event_title: 'potluck',
      event_start: '2026-10-12T18:00:00',
      already_responded: false,
      is_open: true,
      ...overrides,
    },
  };
}

function apiError(status: number, code: string) {
  return Object.assign(new Error('fail'), {
    isAxiosError: true,
    response: { status, data: { detail: [{ code, params: {} }] } },
  });
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('FeedbackScreen', () => {
  it('shows the event header and anonymity note', async () => {
    mockedGet.mockResolvedValueOnce(wireFeedback());
    renderScreen();

    expect(await screen.findByText('feedback for: potluck · oct 12')).toBeInTheDocument();
    expect(
      screen.getByText('your answers are anonymous — hosts see what you wrote, not who wrote it'),
    ).toBeInTheDocument();
    expect(mockedGet).toHaveBeenCalledWith('/api/community/event-feedback/', {
      headers: { 'X-Feedback-Token': 'tok-1' },
    });
  });

  it('omits the date when the event has no start', async () => {
    mockedGet.mockResolvedValueOnce(wireFeedback({ event_start: null }));
    renderScreen();
    expect(await screen.findByText('feedback for: potluck')).toBeInTheDocument();
  });

  it('blocks submit when a required question is empty', async () => {
    mockedGet.mockResolvedValueOnce(wireFeedback());
    renderScreen();

    fireEvent.click(await screen.findByRole('button', { name: 'submit' }));

    expect(await screen.findByText('required', { selector: 'p' })).toBeInTheDocument();
    expect(mockedPost).not.toHaveBeenCalled();
  });

  it('submits answers and shows the fallback confirmation', async () => {
    mockedGet.mockResolvedValue(wireFeedback());
    mockedPost.mockResolvedValueOnce({ data: { confirmation_message: '' } });
    renderScreen();

    fireEvent.change(await screen.findByLabelText('thoughts · required'), {
      target: { value: 'great night' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'submit' }));

    expect(await screen.findByText('thanks for sharing 🌱')).toBeInTheDocument();
    expect(mockedPost).toHaveBeenCalledWith(
      '/api/community/event-feedback/respond/',
      { answers: { q1: 'great night' } },
      { headers: { 'X-Feedback-Token': 'tok-1' } },
    );
  });

  it('shows the survey confirmation message when set', async () => {
    mockedGet.mockResolvedValue(wireFeedback());
    mockedPost.mockResolvedValueOnce({ data: { confirmation_message: 'Cheers friend' } });
    renderScreen();

    fireEvent.change(await screen.findByLabelText('thoughts · required'), {
      target: { value: 'fun' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'submit' }));

    expect(await screen.findByText('cheers friend')).toBeInTheDocument();
  });

  it('shows the already-shared state', async () => {
    mockedGet.mockResolvedValueOnce(wireFeedback({ already_responded: true }));
    renderScreen();
    expect(
      await screen.findByText('you already shared feedback for this one — thank you 🌱'),
    ).toBeInTheDocument();
  });

  it.each([
    ['closed', { is_open: false }],
    ['unmarked', { survey: null }],
  ])('shows the closed state when %s', async (_name, overrides) => {
    mockedGet.mockResolvedValueOnce(wireFeedback(overrides));
    renderScreen();
    expect(await screen.findByText('feedback for this event is closed')).toBeInTheDocument();
  });

  it('shows the invalid-link state on a 404 link error', async () => {
    mockedGet.mockRejectedValueOnce(apiError(404, 'survey.feedback_link_invalid'));
    renderScreen();
    expect(
      await screen.findByText("this feedback link doesn't work — it may have expired"),
    ).toBeInTheDocument();
  });

  it('shows the closed state when the survey was unmarked', async () => {
    mockedGet.mockRejectedValueOnce(apiError(404, 'survey.not_found'));
    renderScreen();
    expect(await screen.findByText('feedback for this event is closed')).toBeInTheDocument();
  });

  it('skips the api and shows the invalid-link state without a hash', () => {
    renderScreen('/feedback');
    expect(
      screen.getByText("this feedback link doesn't work — it may have expired"),
    ).toBeInTheDocument();
    expect(mockedGet).not.toHaveBeenCalled();
  });

  it('flips to the already-shared state when submit reports a duplicate', async () => {
    mockedGet.mockResolvedValue(wireFeedback());
    mockedPost.mockRejectedValueOnce(apiError(400, 'survey.feedback_already_submitted'));
    renderScreen();

    fireEvent.change(await screen.findByLabelText('thoughts · required'), {
      target: { value: 'again' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'submit' }));

    expect(
      await screen.findByText('you already shared feedback for this one — thank you 🌱'),
    ).toBeInTheDocument();
  });

  it.each([
    ['closed', 'survey.closed'],
    ['not found', 'survey.not_found'],
  ])('flips to the closed state when submit reports %s', async (_name, code) => {
    mockedGet.mockResolvedValue(wireFeedback());
    mockedPost.mockRejectedValueOnce(apiError(400, code));
    renderScreen();

    fireEvent.change(await screen.findByLabelText('thoughts · required'), {
      target: { value: 'late' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'submit' }));

    expect(await screen.findByText('feedback for this event is closed')).toBeInTheDocument();
  });

  it('keeps the form and shows an alert on a generic submit failure', async () => {
    mockedGet.mockResolvedValue(wireFeedback());
    mockedPost.mockRejectedValueOnce(new Error('network down'));
    renderScreen();

    fireEvent.change(await screen.findByLabelText('thoughts · required'), {
      target: { value: 'oops' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'submit' }));

    expect(await screen.findByRole('alert')).toHaveTextContent("couldn't submit — try again");
    expect(screen.getByLabelText('thoughts · required')).toHaveValue('oops');
  });
});
