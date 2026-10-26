import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { AxiosError, type AxiosResponse } from 'axios';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type * as SurveysApi from '@/api/surveys';
import type { Survey } from '@/api/surveys';
import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';

const useSurveyMock = vi.fn();

vi.mock('@/api/surveys', async (importOriginal) => {
  const actual = await importOriginal<typeof SurveysApi>();
  return {
    ...actual,
    useSurvey: (slug: string | undefined) => useSurveyMock(slug) as unknown,
    useSubmitSurvey: () => ({ mutateAsync: vi.fn(), isPending: false, reset: vi.fn() }),
  };
});

const { default: SurveyScreen } = await import('./SurveyScreen');

const survey: Survey = {
  id: 's1',
  title: 'diet survey',
  description: '',
  slug: 'diet',
  visibility: 'public',
  isActive: true,
  oneResponsePerUser: false,
  opensAt: null,
  closesAt: null,
  maxResponses: null,
  responseCount: 0,
  linkedEventId: null,
  feedbackEventType: '',
  myResponseId: null,
  myAnswers: null,
  pollResult: null,
  anonymous: false,
  confirmationMessage: '',
  questions: [],
};

function mockNotFound() {
  const err = new AxiosError('not found');
  err.response = { status: 404, data: {} } as AxiosResponse;
  useSurveyMock.mockReturnValue({ data: undefined, isPending: false, isError: true, error: err });
}

function renderScreen() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={['/surveys/diet?ref=email']}>
        <Routes>
          <Route path="/surveys/:slug" element={<SurveyScreen />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const loginHref = `/login?redirect=${encodeURIComponent('/surveys/diet?ref=email')}`;

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
});

describe('SurveyScreen login prompts', () => {
  it('shows a log in button when a signed-out visitor hits a members-only (404) survey', () => {
    mockNotFound();
    renderScreen();

    expect(screen.getByText('log in to see this survey')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'log in' })).toHaveAttribute('href', loginHref);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows the generic error for a 404 when already signed in', () => {
    useAuthStore.setState({ status: 'authed', user: { id: 'u1' } as User, accessToken: 'tok' });
    mockNotFound();
    renderScreen();

    expect(screen.getByRole('alert')).toHaveTextContent("couldn't load the survey");
    expect(screen.queryByRole('link', { name: 'log in' })).not.toBeInTheDocument();
  });

  it('offers a log in link above a public survey for signed-out visitors', () => {
    useSurveyMock.mockReturnValue({ data: survey, isPending: false, isError: false });
    renderScreen();

    expect(screen.getByRole('link', { name: 'log in' })).toHaveAttribute('href', loginHref);
    expect(screen.getByText(/to answer from your account/)).toBeInTheDocument();
  });

  it('says answers stay anonymous on an anonymous survey', () => {
    useSurveyMock.mockReturnValue({
      data: { ...survey, anonymous: true },
      isPending: false,
      isError: false,
    });
    renderScreen();

    expect(screen.getByRole('link', { name: 'log in' })).toBeInTheDocument();
    expect(screen.getByText(/your answers stay anonymous either way/)).toBeInTheDocument();
  });

  it('hides the log in link for signed-in members', () => {
    useAuthStore.setState({ status: 'authed', user: { id: 'u1' } as User, accessToken: 'tok' });
    useSurveyMock.mockReturnValue({ data: survey, isPending: false, isError: false });
    renderScreen();

    expect(screen.queryByRole('link', { name: 'log in' })).not.toBeInTheDocument();
  });
});
