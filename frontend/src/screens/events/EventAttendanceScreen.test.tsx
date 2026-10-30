import { screen } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useEvent } from '@/api/events';
import { setAuthed } from '@/test/auth';
import { CREATOR, makeEvent, NON_HOST } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import EventAttendanceScreen from './EventAttendanceScreen';

vi.mock('@/api/events', () => ({
  useEvent: vi.fn(),
  eventKeys: { all: ['events'], list: vi.fn(), detail: vi.fn() },
}));

vi.mock('@/api/eventStats', () => ({
  useEventStats: vi.fn().mockReturnValue({ data: undefined, isLoading: true, isError: false }),
  useSetAttendance: () => ({ mutate: vi.fn(), isPending: false }),
}));

const BASE_EVENT = makeEvent({
  title: 'Spring Potluck',
  createdById: 'user-creator',
  coHostIds: ['user-creator'],
  guests: [],
});

function renderScreen() {
  return renderWithProviders(
    <Routes>
      <Route path="/events/:id/check-in" element={<EventAttendanceScreen />} />
      <Route path="/events/:id" element={<div>event detail</div>} />
    </Routes>,
    { route: '/events/ev1/check-in' },
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
    setAuthed(CREATOR);
    renderScreen();

    expect(screen.getByRole('heading', { name: /check-in/i })).toBeInTheDocument();
    expect(screen.getByText(BASE_EVENT.title)).toBeInTheDocument();
  });

  it('blocks non-host members with a forbidden notice', () => {
    setAuthed(NON_HOST);
    renderScreen();

    expect(screen.getByText(/only the host or a co-host/i)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /^check-in$/i })).not.toBeInTheDocument();
  });

  it('blocks even the creator when rsvp is disabled', () => {
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
    setAuthed(CREATOR);
    renderScreen();

    expect(screen.getByText(/rsvps are off for this event/i)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /^check-in$/i })).not.toBeInTheDocument();
  });
});
