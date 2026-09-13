import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useSurveys } from '@/api/surveys';
import { useAuthStore } from '@/auth/store';

import SurveysScreen from './SurveysScreen';

vi.mock('@/api/surveys', () => ({
  useSurveys: vi.fn(),
}));

const mockUseSurveys = vi.mocked(useSurveys);

function mockResult(overrides: Partial<ReturnType<typeof useSurveys>>) {
  mockUseSurveys.mockReturnValue({
    isPending: false,
    isError: false,
    data: [],
    ...overrides,
  } as ReturnType<typeof useSurveys>);
}

function renderScreen() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <SurveysScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
});

describe('SurveysScreen', () => {
  it('shows loading indicator while fetching', () => {
    mockResult({ isPending: true, data: undefined });

    renderScreen();

    expect(screen.getByText('loading…')).toBeInTheDocument();
  });

  it('shows an error message when the request fails', () => {
    mockResult({ isError: true, data: undefined });

    renderScreen();

    expect(screen.getByRole('alert')).toHaveTextContent("couldn't load surveys");
  });

  it('shows an empty state when nothing is open', () => {
    mockResult({ data: [] });

    renderScreen();

    expect(screen.getByText('nothing open right now')).toBeInTheDocument();
  });

  it('links each survey to its detail route with lowercase text', () => {
    mockResult({
      data: [
        {
          id: '1',
          title: 'Community Vibes',
          slug: 'community-vibes',
          description: 'Tell Us What You Think',
          visibility: 'public',
          linkedEventId: null,
        },
        {
          id: '2',
          title: 'Members Only Poll',
          slug: 'members-poll',
          description: '',
          visibility: 'members_only',
          linkedEventId: 'event-1',
        },
      ],
    });

    renderScreen();

    const link = screen.getByRole('link', { name: /community vibes/ });
    expect(link).toHaveAttribute('href', '/surveys/community-vibes');
    expect(screen.getByText('tell us what you think')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /members only poll/ })).toHaveAttribute(
      'href',
      '/surveys/members-poll',
    );
  });

  it('tells anonymous visitors that logging in reveals more', () => {
    mockResult({ data: [] });

    renderScreen();

    expect(screen.getByText(/log in to see member-only ones too/)).toBeInTheDocument();
  });
});
