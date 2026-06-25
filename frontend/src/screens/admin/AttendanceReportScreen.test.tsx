import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { EventAttendanceRow } from '@/api/attendanceReport';

vi.mock('@/api/attendanceReport', () => ({
  useAttendanceReport: vi.fn(),
}));

import AttendanceReportScreen from './AttendanceReportScreen';
import { useAttendanceReport } from '@/api/attendanceReport';

const mockUseReport = vi.mocked(useAttendanceReport);

function mockResult(overrides: Partial<ReturnType<typeof useAttendanceReport>>) {
  mockUseReport.mockReturnValue({
    isPending: false,
    isError: false,
    data: [],
    ...overrides,
  } as ReturnType<typeof useAttendanceReport>);
}

function makeRow(overrides: Partial<EventAttendanceRow> = {}): EventAttendanceRow {
  return {
    eventId: 'e1',
    title: 'Potluck',
    startDatetime: new Date('2026-03-15T18:00:00Z'),
    attendedCount: 4,
    noShowCount: 1,
    goingCount: 6,
    ...overrides,
  };
}

function renderScreen() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AttendanceReportScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('AttendanceReportScreen', () => {
  it('renders per-event attended / no-show / going counts', () => {
    mockResult({ data: [makeRow()] });

    renderScreen();

    expect(screen.getByText('potluck')).toBeInTheDocument();
    const row = screen.getByRole('link');
    expect(row).toHaveTextContent('4 attended');
    expect(row).toHaveTextContent('1 no-show');
    expect(row).toHaveTextContent('6 going');
    expect(row).toHaveAttribute('href', '/events/e1');
  });

  it('shows the empty state when nothing is marked', () => {
    mockResult({ data: [] });

    renderScreen();

    expect(screen.getByText(/no attendance marked yet/i)).toBeInTheDocument();
  });

  it('shows an error message when the query fails', () => {
    mockResult({ isError: true, data: undefined });

    renderScreen();

    expect(screen.getByRole('alert')).toHaveTextContent(/couldn't load attendance/i);
  });

  it('shows a loading state while pending', () => {
    mockResult({ isPending: true, data: undefined });

    renderScreen();

    expect(screen.getByText('loading…')).toBeInTheDocument();
  });
});
