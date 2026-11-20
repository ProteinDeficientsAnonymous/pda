import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useCheckInReport } from '@/api/eventCheckInReport';
import { useEvent } from '@/api/events';
import { Code } from '@/api/validationCodes';
import { apiError } from '@/test/apiError';
import { setAuthed } from '@/test/auth';
import { creator, makeEvent, nonHost } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import EventCheckInReportScreen from './EventCheckInReportScreen';

vi.mock('@/api/events', () => ({
  useEvent: vi.fn(),
  eventKeys: { all: ['events'], list: vi.fn(), detail: vi.fn() },
}));

vi.mock('@/api/eventCheckInReport', () => ({
  useCheckInReport: vi.fn().mockReturnValue({ data: undefined, isLoading: true, isError: false }),
  downloadCheckInReportCsv: vi.fn(),
  CSV_COLUMNS: [
    { key: 'name', label: 'name' },
    { key: 'attendance', label: 'attendance' },
  ],
}));

const BASE_EVENT = makeEvent({
  title: 'Spring Potluck',
  createdById: 'user-creator',
  coHostIds: ['user-creator'],
  isPast: true,
  guests: [],
});

function renderScreen() {
  return renderWithProviders(
    <Routes>
      <Route path="/events/:id/report" element={<EventCheckInReportScreen />} />
      <Route path="/events/:id" element={<div>event detail</div>} />
    </Routes>,
    { route: '/events/ev1/report' },
  );
}

beforeEach(() => {
  vi.mocked(useEvent).mockReturnValue({
    data: BASE_EVENT,
    isPending: false,
    isError: false,
  } as ReturnType<typeof useEvent>);
});

describe('EventCheckInReportScreen', () => {
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

  it('renders the report heading for the event creator', () => {
    setAuthed(creator);
    renderScreen();

    expect(screen.getByRole('heading', { name: /check-in report/i })).toBeInTheDocument();
    expect(screen.getByText(BASE_EVENT.title)).toBeInTheDocument();
  });

  it('back link returns to the event, not the attendance page', async () => {
    setAuthed(creator);
    renderScreen();

    await userEvent.click(screen.getByRole('link', { name: /back to event/i }));

    expect(screen.getByText('event detail')).toBeInTheDocument();
  });

  it('blocks non-host members with a forbidden notice', () => {
    setAuthed(nonHost);
    renderScreen();

    expect(screen.getByText(/only the host or a co-host/i)).toBeInTheDocument();
    expect(screen.queryByText(BASE_EVENT.title)).not.toBeInTheDocument();
  });

  it('splits unmarked guests into were-going and maybe sections, with no didnt-go section', () => {
    const person = (userId: string, name: string) => ({
      userId,
      name,
      phone: null,
      isMember: true,
      isPlusOneGuest: false,
    });
    vi.mocked(useCheckInReport).mockReturnValue({
      data: {
        attendedCount: 0,
        noShowCount: 0,
        canceledCount: 0,
        unmarkedGoingCount: 1,
        unmarkedNotGoingCount: 1,
        attended: [],
        noShows: [],
        canceled: [],
        unmarkedGoing: [person('u1', 'Going Guest')],
        unmarkedNotGoing: [person('u2', 'Maybe Guest')],
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useCheckInReport>);
    setAuthed(creator);
    renderScreen();

    expect(screen.getByText('unmarked — were going')).toBeInTheDocument();
    expect(screen.getByText('Going Guest')).toBeInTheDocument();
    expect(screen.getByText('unmarked — maybe or waitlisted')).toBeInTheDocument();
    expect(screen.getByText('Maybe Guest')).toBeInTheDocument();
    expect(screen.queryByText("no one marked didn't go")).not.toBeInTheDocument();
  });
});
