import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';

import SurveyScreen from './SurveyScreen';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), put: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

function renderScreen(slug = 'feedback') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/surveys/${slug}`]}>
        <Routes>
          <Route path="/surveys/:slug" element={<SurveyScreen />} />
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
    mockedGet.mockResolvedValueOnce({ data: baseWireSurvey });
    renderScreen();

    fireEvent.click(await screen.findByRole('button', { name: 'submit' }));

    expect(await screen.findByText('required')).toBeInTheDocument();
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

    fireEvent.change(await screen.findByLabelText('thoughts'), {
      target: { value: 'great job' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'submit' }));

    await waitFor(() => {
      expect(mockedPost).toHaveBeenCalledWith('/api/community/surveys/view/feedback/respond/', {
        answers: { q1: 'great job' },
      });
    });
    expect(await screen.findByText('saved ✓')).toBeInTheDocument();
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
    expect(screen.getByLabelText('thoughts')).toHaveValue('previous answer');
  });
});
