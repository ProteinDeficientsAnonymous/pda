import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { type RestoredMember, useRestoredMembers } from '@/api/restoredMembers';
import { useUpdateUser } from '@/api/users';
import { renderWithProviders } from '@/test/render';

import { RestoredMembersList } from './RestoredMembersList';

vi.mock('@/api/restoredMembers', () => ({ useRestoredMembers: vi.fn() }));
vi.mock('@/api/users', () => ({ useUpdateUser: vi.fn() }));

const day = (d: string) => new Date(`2026-${d}T12:00:00Z`);
const member: RestoredMember = {
  id: 'u1',
  fullName: 'Ada Lovelace',
  phoneNumber: '+16505550001',
  restoredAt: day('03-04'),
  hasJoinedWhatsapp: false,
  recentEvents: [
    { eventId: 'e2', title: 'Potluck', startDatetime: day('03-01'), eventType: 'official' },
    { eventId: 'e1', title: 'Book Club', startDatetime: day('02-10'), eventType: 'club' },
  ],
};
const mutateAsync = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useRestoredMembers).mockReturnValue({
    data: [member],
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof useRestoredMembers>);
  vi.mocked(useUpdateUser).mockReturnValue({
    mutateAsync,
    isPending: false,
  } as unknown as ReturnType<typeof useUpdateUser>);
});

describe('RestoredMembersList', () => {
  it('shows the restored date and last events', () => {
    renderWithProviders(<RestoredMembersList query="" />);

    expect(screen.getByText('Ada Lovelace')).toBeInTheDocument();
    expect(screen.getByText(/restored mar 4, 2026/)).toBeInTheDocument();
    expect(screen.getByText('latest qualifying events')).toBeInTheDocument();
    expect(screen.getByText('potluck — mar 1, 2026 · official')).toBeInTheDocument();
    expect(screen.getByText('book club — feb 10, 2026 · club')).toBeInTheDocument();
  });

  it('flips joined whatsapp for the restored member', async () => {
    renderWithProviders(<RestoredMembersList query="" />);

    await userEvent.click(screen.getByRole('switch', { name: /joined whatsapp/i }));

    expect(useUpdateUser).toHaveBeenCalledWith('u1');
    expect(mutateAsync).toHaveBeenCalledWith({ hasJoinedWhatsapp: true });
  });

  it('filters by search query', () => {
    renderWithProviders(<RestoredMembersList query="grace" />);

    expect(screen.queryByText('Ada Lovelace')).not.toBeInTheDocument();
    expect(screen.getByText(/nothing matches/)).toBeInTheDocument();
  });
});
