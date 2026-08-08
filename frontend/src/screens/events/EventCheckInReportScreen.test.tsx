import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useEvent } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import { makeEvent, makeUser } from '@/test/fixtures';

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

const CREATOR = makeUser({ id: 'user-creator', firstName: 'Alice', fullName: 'Alice' });
const nonMember = makeUser({ id: 'user-nonmember', firstName: 'Casey', fullName: 'Casey' });

function renderScreen() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/events/ev1/report']}>
        <Routes>
          <Route path="/events/:id/report" element={<EventCheckInReportScreen />} />
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

describe('EventCheckInReportScreen', () => {
  it('renders the report heading for the event creator', () => {
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByRole('heading', { name: /check-in report/i })).toBeInTheDocument();
    expect(screen.getByText(BASE_EVENT.title)).toBeInTheDocument();
  });

  it('back link returns to the event, not the attendance page', async () => {
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    await userEvent.click(screen.getByRole('link', { name: /back to event/i }));

    expect(screen.getByText('event detail')).toBeInTheDocument();
  });

  it('blocks non-host members with a forbidden notice', () => {
    useAuthStore.setState({ status: 'authed', user: nonMember, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByText(/only the host or a co-host/i)).toBeInTheDocument();
    expect(screen.queryByText(BASE_EVENT.title)).not.toBeInTheDocument();
  });
});
