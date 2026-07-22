import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/attendanceReport', () => ({
  useAttendanceReport: vi.fn(),
}));
vi.mock('@/api/featureFlags', () => ({
  useFeatureFlags: vi.fn(),
  useFlag: vi.fn(),
}));
vi.mock('./MemberAttendanceTab', () => ({
  MemberAttendanceTab: () => <div>members tab content</div>,
}));

import { useAttendanceReport } from '@/api/attendanceReport';
import { useFlag } from '@/api/featureFlags';
import { makeRow } from '@/test/fixtures';

import AttendanceReportScreen from './AttendanceReportScreen';

const mockUseReport = vi.mocked(useAttendanceReport);
const mockUseFlag = vi.mocked(useFlag);

function mockResult(overrides: Partial<ReturnType<typeof useAttendanceReport>>) {
  mockUseReport.mockReturnValue({
    isPending: false,
    isError: false,
    data: [],
    ...overrides,
  } as ReturnType<typeof useAttendanceReport>);
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
  mockUseFlag.mockReturnValue(false);
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
    expect(row).toHaveAttribute('href', '/events/e1/report');
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

  it('hides the members tab when the flag is off', () => {
    mockResult({ data: [] });
    mockUseFlag.mockReturnValue(false);

    renderScreen();

    expect(screen.queryByRole('tablist')).not.toBeInTheDocument();
  });

  it('switches to the members tab when the flag is on', async () => {
    mockResult({ data: [] });
    mockUseFlag.mockReturnValue(true);
    const user = userEvent.setup();

    renderScreen();
    await user.click(screen.getByRole('tab', { name: 'members' }));

    expect(screen.getByText('members tab content')).toBeInTheDocument();
  });
});
