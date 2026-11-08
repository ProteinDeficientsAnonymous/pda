import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { type RestoredMember, useRestoredMembers } from '@/api/restoredMembers';
import { useUpdateUser } from '@/api/users';
import { renderWithProviders } from '@/test/render';

import { RestoredMembersList } from './RestoredMembersList';

vi.mock('@/api/restoredMembers', () => ({ useRestoredMembers: vi.fn() }));
vi.mock('@/api/users', () => ({ useUpdateUser: vi.fn() }));

const member: RestoredMember = {
  id: 'u1',
  full_name: 'Ada Lovelace',
  phone_number: '+16505550001',
  restored_at: '2026-03-04T12:00:00Z',
  has_joined_whatsapp: false,
  recent_events: [
    { event_id: 'e2', title: 'Potluck', start_datetime: '2026-03-01T12:00:00Z' },
    { event_id: 'e1', title: 'Book Club', start_datetime: '2026-02-10T12:00:00Z' },
  ],
};

function mockMembers(data: RestoredMember[]) {
  vi.mocked(useRestoredMembers).mockReturnValue({
    data,
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof useRestoredMembers>);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('RestoredMembersList', () => {
  it('shows the restored date and last events', () => {
    mockMembers([member]);
    vi.mocked(useUpdateUser).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useUpdateUser>);
    renderWithProviders(<RestoredMembersList query="" />);

    expect(screen.getByText('Ada Lovelace')).toBeInTheDocument();
    expect(screen.getByText(/restored mar 4, 2026/)).toBeInTheDocument();
    expect(screen.getByText('Potluck · mar 1, 2026')).toBeInTheDocument();
    expect(screen.getByText('Book Club · feb 10, 2026')).toBeInTheDocument();
  });

  it('flips joined whatsapp for the restored member', async () => {
    mockMembers([member]);
    const mutateAsync = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useUpdateUser).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useUpdateUser>);
    renderWithProviders(<RestoredMembersList query="" />);

    await userEvent.click(screen.getByRole('switch', { name: /joined whatsapp/i }));

    expect(useUpdateUser).toHaveBeenCalledWith('u1');
    expect(mutateAsync).toHaveBeenCalledWith({ hasJoinedWhatsapp: true });
  });

  it('filters by search query', () => {
    mockMembers([member]);
    renderWithProviders(<RestoredMembersList query="grace" />);

    expect(screen.queryByText('Ada Lovelace')).not.toBeInTheDocument();
    expect(screen.getByText(/nothing matches/)).toBeInTheDocument();
  });
});
