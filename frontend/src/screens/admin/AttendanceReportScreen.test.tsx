import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAttendanceReport } from '@/api/attendanceReport';
import { makeRow } from '@/test/fixtures';

import AttendanceReportScreen from './AttendanceReportScreen';

vi.mock('@/api/attendanceReport', () => ({
  useAttendanceReport: vi.fn(),
}));
vi.mock('./MemberAttendanceTab', () => ({
  MemberAttendanceTab: () => <div>members tab content</div>,
}));
vi.mock('@/api/attendanceImport', () => ({
  useAttendanceImportEventOptions: vi.fn(() => ({ data: [] })),
  usePreviewAttendanceImport: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useCommitAttendanceImport: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

const mockUseReport = vi.mocked(useAttendanceReport);

function mockResult(overrides: Partial<ReturnType<typeof useAttendanceReport>>) {
  mockUseReport.mockReturnValue({
    isPending: false,
    isError: false,
    data: {
      events: [],
      officialNoShowCount: 0,
      clubNoShowCount: 0,
    },
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
});

describe('AttendanceReportScreen', () => {
  it('renders per-event attended / no-show counts', () => {
    mockResult({
      data: {
        events: [makeRow()],
        officialNoShowCount: 1,
        clubNoShowCount: 0,
      },
    });

    renderScreen();

    expect(screen.getByText('potluck')).toBeInTheDocument();
    const row = screen.getByRole('link');
    expect(row).toHaveTextContent('4 attended');
    expect(row).toHaveTextContent('1 no-show');
    expect(row).toHaveAttribute('href', '/events/e1/report');
  });

  it('shows the empty state when nothing is marked', () => {
    mockResult({
      data: {
        events: [],
        officialNoShowCount: 0,
        clubNoShowCount: 0,
      },
    });

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

  it('switches to the members tab', async () => {
    mockResult({
      data: {
        events: [],
        officialNoShowCount: 0,
        clubNoShowCount: 0,
      },
    });
    const user = userEvent.setup();

    renderScreen();
    await user.click(screen.getByRole('tab', { name: 'members' }));

    expect(screen.getByText('members tab content')).toBeInTheDocument();
  });

  it('opens the partiful import dialog from the import button', async () => {
    mockResult({
      data: {
        events: [],
        officialNoShowCount: 0,
        clubNoShowCount: 0,
      },
    });
    const user = userEvent.setup();

    renderScreen();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'import from partiful' }));

    expect(screen.getByRole('dialog', { name: 'import partiful attendance' })).toBeInTheDocument();
  });
});
