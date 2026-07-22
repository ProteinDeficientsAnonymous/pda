import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  type MemberAttendanceRow,
  useMemberAttendanceAnalytics,
} from '@/api/memberAttendanceAnalytics';
import { useUpdateUser } from '@/api/users';
import { useAuthStore } from '@/auth/store';

import { MemberAttendanceTab } from './MemberAttendanceTab';

vi.mock('@/api/memberAttendanceAnalytics', () => ({
  useMemberAttendanceAnalytics: vi.fn(),
}));

vi.mock('@/api/users', () => ({
  useUpdateUser: vi.fn(),
}));

vi.mock('@/auth/store', () => ({
  useAuthStore: vi.fn(),
}));

const mockUseAnalytics = vi.mocked(useMemberAttendanceAnalytics);
const mockUseUpdateUser = vi.mocked(useUpdateUser);
const mockUseAuthStore = vi.mocked(useAuthStore);

function makeMemberRow(overrides: Partial<MemberAttendanceRow> = {}): MemberAttendanceRow {
  return {
    userId: 'u1',
    fullName: 'Ada Lovelace',
    phoneNumber: '+12025550101',
    isPaused: false,
    lastQualifyingAt: new Date('2026-01-01T00:00:00Z'),
    qualifyingCount12mo: 3,
    compliant: true,
    communityCount: 1,
    noShowCount: 0,
    cancelCount: 0,
    monthsSinceLastQualifying: 2,
    isPauseCandidate: false,
    ...overrides,
  };
}

const updateMutateAsync = vi.fn();

function mockUser(canManageUsers: boolean) {
  mockUseAuthStore.mockImplementation((selector) =>
    selector({
      user: {
        roles: canManageUsers
          ? [{ name: 'admin', isDefault: false, permissions: ['manage_users'] }]
          : [],
      },
    } as unknown as Parameters<typeof selector>[0]),
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  updateMutateAsync.mockReset();
  updateMutateAsync.mockResolvedValue(undefined);
  mockUseUpdateUser.mockReturnValue({
    mutateAsync: updateMutateAsync,
    isPending: false,
  } as unknown as ReturnType<typeof useUpdateUser>);
  mockUser(false);
});

function mockRows(rows: MemberAttendanceRow[]) {
  mockUseAnalytics.mockReturnValue({
    data: rows,
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof useMemberAttendanceAnalytics>);
}

describe('MemberAttendanceTab', () => {
  it('shows the empty state with no members', () => {
    mockRows([]);
    render(<MemberAttendanceTab />);
    expect(screen.getByText(/nothing here/i)).toBeInTheDocument();
  });

  it('renders member stats', () => {
    mockRows([makeMemberRow()]);
    render(<MemberAttendanceTab />);
    expect(screen.getByText('ada lovelace')).toBeInTheDocument();
    expect(screen.getByText('compliant')).toBeInTheDocument();
  });

  it('shows a pause-candidate badge for members overdue on qualifying attendance', () => {
    mockRows([
      makeMemberRow({ isPauseCandidate: true, lastQualifyingAt: null, qualifyingCount12mo: 0 }),
    ]);
    render(<MemberAttendanceTab />);
    expect(screen.getByText('pause candidate')).toBeInTheDocument();
    expect(screen.getByText(/never attended a qualifying event/)).toBeInTheDocument();
  });

  it('filters to at-risk members only', async () => {
    mockRows([
      makeMemberRow({ userId: 'u1', fullName: 'Compliant Member' }),
      makeMemberRow({
        userId: 'u2',
        fullName: 'Risky Member',
        isPauseCandidate: true,
        lastQualifyingAt: null,
      }),
    ]);
    const user = userEvent.setup();
    render(<MemberAttendanceTab />);

    await user.click(screen.getByRole('button', { name: 'at risk' }));

    expect(screen.queryByText('compliant member')).not.toBeInTheDocument();
    expect(screen.getByText('risky member')).toBeInTheDocument();
  });

  it('hides the pause button without manage_users permission', () => {
    mockRows([makeMemberRow()]);
    mockUser(false);
    render(<MemberAttendanceTab />);
    expect(screen.queryByRole('button', { name: 'pause member' })).not.toBeInTheDocument();
  });

  it('pauses a member when confirmed, with manage_users permission', async () => {
    mockRows([makeMemberRow({ userId: 'u9' })]);
    mockUser(true);
    const user = userEvent.setup();
    render(<MemberAttendanceTab />);

    await user.click(screen.getByRole('button', { name: 'pause member' }));
    await user.click(screen.getByRole('button', { name: 'pause' }));

    expect(updateMutateAsync).toHaveBeenCalledWith({ isPaused: true });
  });

  it('does not call the pause mutation when the confirmation is cancelled', async () => {
    mockRows([makeMemberRow()]);
    mockUser(true);
    const user = userEvent.setup();
    render(<MemberAttendanceTab />);

    await user.click(screen.getByRole('button', { name: 'pause member' }));
    await user.click(screen.getByRole('button', { name: 'cancel' }));

    expect(updateMutateAsync).not.toHaveBeenCalled();
  });

  it('shows a paused badge and hides the pause button for already-paused members', () => {
    mockRows([makeMemberRow({ isPaused: true })]);
    mockUser(true);
    render(<MemberAttendanceTab />);
    expect(screen.getByText('paused')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'pause member' })).not.toBeInTheDocument();
  });
});
