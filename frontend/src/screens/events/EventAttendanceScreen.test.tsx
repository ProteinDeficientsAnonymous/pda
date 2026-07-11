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

vi.mock('@/api/eventStats', () => ({
  useEventStats: vi.fn().mockReturnValue({ data: undefined, isLoading: true, isError: false }),
  useSetAttendance: () => ({ mutate: vi.fn(), isPending: false }),
}));

import { useEvent } from '@/api/events';

import EventAttendanceScreen from './EventAttendanceScreen';

const BASE_EVENT = makeEvent({
  title: 'Spring Potluck',
  createdById: 'user-creator',
  guests: [],
});

const CREATOR = makeUser({ id: 'user-creator', displayName: 'Alice' });
const nonMember = makeUser({ id: 'user-nonmember', displayName: 'Casey' });

function renderScreen() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/events/ev1/attendance']}>
        <Routes>
          <Route path="/events/:id/attendance" element={<EventAttendanceScreen />} />
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

describe('EventAttendanceScreen', () => {
  it('renders the panel for the event creator', () => {
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByRole('heading', { name: /attendance/i })).toBeInTheDocument();
    expect(screen.getByText(BASE_EVENT.title)).toBeInTheDocument();
  });

  it('blocks non-host members with a forbidden notice', () => {
    useAuthStore.setState({ status: 'authed', user: nonMember, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByText(/only the host or a co-host/i)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /^attendance$/i })).not.toBeInTheDocument();
  });

  it('blocks even the creator when rsvp is disabled', () => {
    vi.mocked(useEvent).mockReturnValue({
      data: makeEvent({ createdById: 'user-creator', guests: [], rsvpEnabled: false }),
      isPending: false,
      isError: false,
    } as ReturnType<typeof useEvent>);
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByText(/only the host or a co-host/i)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /^attendance$/i })).not.toBeInTheDocument();
  });
});
