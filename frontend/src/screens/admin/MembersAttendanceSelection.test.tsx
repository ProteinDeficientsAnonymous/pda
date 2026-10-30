import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAttendanceImportEventOptions } from '@/api/attendanceImport';
import { useMarkAttendance } from '@/api/attendanceMark';
import { useRoles } from '@/api/roles';
import { useUsers } from '@/api/users';
import { Permission } from '@/models/permissions';
import type { User } from '@/models/user';
import { setAuthed } from '@/test/auth';
import { makeMember, makeUserWithPermissions } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import MembersScreen from './MembersScreen';

vi.mock('@/api/users', () => ({
  useUsers: vi.fn(),
  useCreateUser: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false, reset: vi.fn() })),
}));

vi.mock('@/api/roles', () => ({ useRoles: vi.fn() }));

vi.mock('@/api/attendanceImport', () => ({
  useAttendanceImportEventOptions: vi.fn(),
}));

vi.mock('@/api/attendanceMark', () => ({
  useMarkAttendance: vi.fn(),
  reportMarkAttendanceError: (err: unknown) => String(err),
}));

const mockUseUsers = vi.mocked(useUsers);
const mockUseMarkAttendance = vi.mocked(useMarkAttendance);
const mutate = vi.fn();

// The built-in "admin" role grants every permission, which would hide the gate.
function staffUser(permissions: string[]): User {
  return makeUserWithPermissions(permissions, { id: 'me', fullName: 'Staff User' });
}

function renderScreen() {
  return renderWithProviders(<MembersScreen />);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useRoles).mockReturnValue({
    data: [],
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof useRoles>);
  vi.mocked(useAttendanceImportEventOptions).mockReturnValue({
    data: [{ id: 'evt-1', title: 'summer potluck', startDatetime: new Date('2023-07-04') }],
  } as unknown as ReturnType<typeof useAttendanceImportEventOptions>);
  mockUseMarkAttendance.mockReturnValue({
    mutate,
    isPending: false,
  } as unknown as ReturnType<typeof useMarkAttendance>);
  mockUseUsers.mockReturnValue({
    isPending: false,
    isError: false,
    data: [
      makeMember({ id: 'm1', fullName: 'Ada Lovelace' }),
      makeMember({ id: 'm2', fullName: 'Grace Hopper' }),
    ],
  } as unknown as ReturnType<typeof useUsers>);
  setAuthed(staffUser([Permission.ManageUsers]));
});

describe('marking members attended from the members screen', () => {
  it('hides the selection checkboxes without the manage users permission', () => {
    setAuthed(staffUser([Permission.ManageEvents]));

    renderScreen();

    expect(
      screen.queryByRole('checkbox', { name: /select ada lovelace/i }),
    ).not.toBeInTheDocument();
  });

  it('offers no mark-attended action until a member is selected', () => {
    renderScreen();

    expect(screen.queryByRole('button', { name: /mark attended/i })).not.toBeInTheDocument();
  });

  it('counts the selected members in the action bar', async () => {
    const user = userEvent.setup();
    renderScreen();

    await user.click(screen.getByRole('checkbox', { name: /select ada lovelace/i }));
    await user.click(screen.getByRole('checkbox', { name: /select grace hopper/i }));

    expect(screen.getByText('2 selected')).toBeInTheDocument();
  });

  it('marks the selected members attended at an existing event', async () => {
    const user = userEvent.setup();
    renderScreen();

    await user.click(screen.getByRole('checkbox', { name: /select ada lovelace/i }));
    await user.click(screen.getByRole('button', { name: /mark attended/i }));
    await user.click(screen.getByRole('button', { name: /summer potluck/i }));
    await user.click(screen.getByRole('button', { name: /^confirm$/i }));

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({ eventId: 'evt-1', userIds: ['m1'] }),
      expect.anything(),
    );
  });

  it('clears the selection when asked', async () => {
    const user = userEvent.setup();
    renderScreen();

    await user.click(screen.getByRole('checkbox', { name: /select ada lovelace/i }));
    await user.click(screen.getByRole('button', { name: /clear selection/i }));

    expect(screen.queryByRole('button', { name: /mark attended/i })).not.toBeInTheDocument();
  });
});
