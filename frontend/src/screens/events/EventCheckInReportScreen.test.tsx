import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useEvent } from '@/api/events';
import { setAuthed } from '@/test/auth';
import { CREATOR, makeEvent, NON_HOST } from '@/test/fixtures';
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
  it('renders the report heading for the event creator', () => {
    setAuthed(CREATOR);
    renderScreen();

    expect(screen.getByRole('heading', { name: /check-in report/i })).toBeInTheDocument();
    expect(screen.getByText(BASE_EVENT.title)).toBeInTheDocument();
  });

  it('back link returns to the event, not the attendance page', async () => {
    setAuthed(CREATOR);
    renderScreen();

    await userEvent.click(screen.getByRole('link', { name: /back to event/i }));

    expect(screen.getByText('event detail')).toBeInTheDocument();
  });

  it('blocks non-host members with a forbidden notice', () => {
    setAuthed(NON_HOST);
    renderScreen();

    expect(screen.getByText(/only the host or a co-host/i)).toBeInTheDocument();
    expect(screen.queryByText(BASE_EVENT.title)).not.toBeInTheDocument();
  });
});
