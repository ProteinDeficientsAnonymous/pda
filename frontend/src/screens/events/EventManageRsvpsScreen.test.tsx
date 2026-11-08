import { screen } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useEvent } from '@/api/events';
import { Code } from '@/api/validationCodes';
import { apiError } from '@/test/apiError';
import { setAuthed } from '@/test/auth';
import { creator, makeEvent, nonHost } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

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

function renderScreen() {
  return renderWithProviders(
    <Routes>
      <Route path="/events/:id/manage-rsvps" element={<EventManageRsvpsScreen />} />
      <Route path="/events/:id" element={<div>event detail</div>} />
    </Routes>,
    { route: '/events/ev1/manage-rsvps' },
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
  it('shows the forbidden notice on a 403', () => {
    vi.mocked(useEvent).mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      error: apiError(403, Code.Event.PermDenied),
    } as unknown as ReturnType<typeof useEvent>);
    renderScreen();

    expect(screen.getByText("you don't have permission to see this event")).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'back to event' })).toHaveAttribute(
      'href',
      '/events/ev1',
    );
  });

  it('shows a forbidden notice for a non-host', () => {
    setAuthed(nonHost);
    renderScreen();

    expect(screen.getByText(/only the host or a co-host/i)).toBeInTheDocument();
  });

  it('lets a host manage rsvps after the event ended', () => {
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
    setAuthed(creator);
    renderScreen();

    expect(screen.getByRole('heading', { name: /manage rsvps/i })).toBeInTheDocument();
    expect(screen.getByText(/anyone you add counts as going/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'check-in' })).toHaveAttribute(
      'href',
      '/events/ev1/check-in',
    );
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
    setAuthed(creator);
    renderScreen();

    expect(screen.getByText(/rsvps are off/i)).toBeInTheDocument();
  });

  it('renders the panel heading for a host on a future rsvp-enabled event', () => {
    setAuthed(creator);
    renderScreen();

    expect(screen.getByRole('heading', { name: /manage rsvps/i })).toBeInTheDocument();
    expect(screen.getByText(BASE_EVENT.title)).toBeInTheDocument();
    expect(screen.queryByText(/anyone you add counts as going/i)).not.toBeInTheDocument();
  });
});
