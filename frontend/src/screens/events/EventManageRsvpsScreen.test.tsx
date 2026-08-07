import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useEvent } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import { makeEvent, makeGuest, makeUser } from '@/test/fixtures';

import EventManageRsvpsScreen from './EventManageRsvpsScreen';

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
      <MemoryRouter initialEntries={['/events/ev1/manage-rsvps']}>
        <Routes>
          <Route path="/events/:id/manage-rsvps" element={<EventManageRsvpsScreen />} />
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

describe('EventManageRsvpsScreen', () => {
  it('shows a forbidden notice for a non-host', () => {
    useAuthStore.setState({ status: 'authed', user: nonMember, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByText(/only the host or a co-host/i)).toBeInTheDocument();
  });

  it('shows a forbidden notice for a past event with no questions', () => {
    vi.mocked(useEvent).mockReturnValue({
      data: makeEvent({
        createdById: 'user-creator',
        coHostIds: ['user-creator'],
        guests: [],
        isPast: true,
      }),
      isPending: false,
      isError: false,
    } as ReturnType<typeof useEvent>);
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByText(/event has already happened/i)).toBeInTheDocument();
  });

  it('lets a host review question responses on a past event', () => {
    vi.mocked(useEvent).mockReturnValue({
      data: makeEvent({
        createdById: 'user-creator',
        coHostIds: ['user-creator'],
        guests: [],
        isPast: true,
        rsvpQuestions: [
          {
            id: 'q1',
            label: 'dietary?',
            fieldType: 'textarea',
            options: [],
            required: false,
          },
        ],
      }),
      isPending: false,
      isError: false,
    } as ReturnType<typeof useEvent>);
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByRole('heading', { name: /manage rsvps/i })).toBeInTheDocument();
    expect(screen.getByText(/guest edits are closed/i)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /question responses/i })).toBeInTheDocument();
  });

  it('shows a forbidden notice when rsvps are disabled', () => {
    vi.mocked(useEvent).mockReturnValue({
      data: makeEvent({
        createdById: 'user-creator',
        coHostIds: ['user-creator'],
        guests: [],
        rsvpEnabled: false,
      }),
      isPending: false,
      isError: false,
    } as ReturnType<typeof useEvent>);
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByText(/rsvps are off/i)).toBeInTheDocument();
  });

  it('lets a host review responses when rsvps are off but questions remain', () => {
    vi.mocked(useEvent).mockReturnValue({
      data: makeEvent({
        createdById: 'user-creator',
        coHostIds: ['user-creator'],
        guests: [],
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
      }),
      isPending: false,
      isError: false,
    } as ReturnType<typeof useEvent>);
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByRole('heading', { name: /manage rsvps/i })).toBeInTheDocument();
    expect(screen.getByText(/reviewing question responses/i)).toBeInTheDocument();
  });

  it('lets a host review responses when only saved answer snapshots remain', () => {
    vi.mocked(useEvent).mockReturnValue({
      data: makeEvent({
        createdById: 'user-creator',
        coHostIds: ['user-creator'],
        rsvpEnabled: false,
        rsvpQuestions: [],
        guests: [
          makeGuest({
            answers: { deleted: { label: 'deleted question', answer: 'saved answer' } },
          }),
        ],
      }),
      isPending: false,
      isError: false,
    } as ReturnType<typeof useEvent>);
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByRole('heading', { name: /manage rsvps/i })).toBeInTheDocument();
    expect(screen.getByText('saved answer')).toBeInTheDocument();
  });

  it('renders the panel heading for a host on a future rsvp-enabled event', () => {
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByRole('heading', { name: /manage rsvps/i })).toBeInTheDocument();
    expect(screen.getByText(BASE_EVENT.title)).toBeInTheDocument();
  });
});
