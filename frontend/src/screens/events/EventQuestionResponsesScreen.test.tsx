import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useEvent } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import { makeEvent, makeGuest, makeUser } from '@/test/fixtures';

import EventQuestionResponsesScreen from './EventQuestionResponsesScreen';

vi.mock('@/api/events', () => ({
  useEvent: vi.fn(),
  eventKeys: { all: ['events'], list: vi.fn(), detail: vi.fn() },
}));

const BASE_EVENT = makeEvent({
  title: 'Spring Potluck',
  createdById: 'user-creator',
  coHostIds: ['user-creator'],
  guests: [],
});

const CREATOR = makeUser({ id: 'user-creator', firstName: 'Alice', fullName: 'Alice' });
const nonMember = makeUser({ id: 'user-nonmember', firstName: 'Casey', fullName: 'Casey' });

function renderScreen() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/events/ev1/responses']}>
        <Routes>
          <Route path="/events/:id/responses" element={<EventQuestionResponsesScreen />} />
          <Route path="/events/:id" element={<div>event detail</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(useEvent).mockReturnValue({
    data: BASE_EVENT,
    isPending: false,
    isError: false,
  } as ReturnType<typeof useEvent>);
});

describe('EventQuestionResponsesScreen', () => {
  it('shows a forbidden notice for a non-host', () => {
    useAuthStore.setState({ status: 'authed', user: nonMember, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByText(/only the host or a co-host/i)).toBeInTheDocument();
  });

  it('shows a notice when the event has no questions', () => {
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByText(/no rsvp questions/i)).toBeInTheDocument();
  });

  it('shows responses on a past event with rsvps off', () => {
    vi.mocked(useEvent).mockReturnValue({
      data: makeEvent({
        createdById: 'user-creator',
        coHostIds: ['user-creator'],
        isPast: true,
        rsvpEnabled: false,
        rsvpQuestions: [
          {
            id: 'q1',
            label: 'dietary?',
            fieldType: 'textarea',
            options: [],
            required: false,
          },
        ],
        guests: [
          makeGuest({ questionnaireResponses: { q1: { label: 'dietary?', answer: 'no nuts' } } }),
        ],
      }),
      isPending: false,
      isError: false,
    } as ReturnType<typeof useEvent>);
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByRole('heading', { name: /question responses/i })).toBeInTheDocument();
    expect(screen.getByText('no nuts')).toBeInTheDocument();
  });

  it('shows saved answers for deleted questions', () => {
    vi.mocked(useEvent).mockReturnValue({
      data: makeEvent({
        createdById: 'user-creator',
        coHostIds: ['user-creator'],
        rsvpQuestions: [],
        guests: [
          makeGuest({
            questionnaireResponses: {
              deleted: { label: 'deleted question', answer: 'saved answer' },
            },
          }),
        ],
      }),
      isPending: false,
      isError: false,
    } as ReturnType<typeof useEvent>);
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByText('saved answer')).toBeInTheDocument();
  });
});
