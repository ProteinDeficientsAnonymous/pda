import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';
import { makeEvent, makeUser } from '@/test/fixtures';

vi.mock('@/api/events', () => ({
  useEvent: vi.fn(),
  eventKeys: { all: ['events'], list: vi.fn(), detail: vi.fn() },
}));

import { useEvent } from '@/api/events';

import EventManageRsvpsScreen from './EventManageRsvpsScreen';

const BASE_EVENT = makeEvent({
  title: 'Spring Potluck',
  createdById: 'user-creator',
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

  it('shows a forbidden notice for a past event', () => {
    vi.mocked(useEvent).mockReturnValue({
      data: makeEvent({ createdById: 'user-creator', guests: [], isPast: true }),
      isPending: false,
      isError: false,
    } as ReturnType<typeof useEvent>);
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByText(/event has already happened/i)).toBeInTheDocument();
  });

  it('shows a forbidden notice when rsvps are disabled', () => {
    vi.mocked(useEvent).mockReturnValue({
      data: makeEvent({ createdById: 'user-creator', guests: [], rsvpEnabled: false }),
      isPending: false,
      isError: false,
    } as ReturnType<typeof useEvent>);
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByText(/rsvps are off/i)).toBeInTheDocument();
  });

  it('renders the panel heading for a host on a future rsvp-enabled event', () => {
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByRole('heading', { name: /manage rsvps/i })).toBeInTheDocument();
    expect(screen.getByText(BASE_EVENT.title)).toBeInTheDocument();
  });
});
