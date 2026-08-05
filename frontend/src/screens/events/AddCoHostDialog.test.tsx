import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { makeEvent } from '@/test/fixtures';

import { AddCoHostDialog } from './AddCoHostDialog';

const updateMutateAsync = vi.hoisted(() => vi.fn());

vi.mock('@/api/eventWrites', () => ({
  useUpdateEvent: () => ({ mutateAsync: updateMutateAsync, isPending: false }),
}));

vi.mock('@/api/userSearch', () => ({
  useUserSearch: () => ({
    data: [
      { id: 'user-accepted', fullName: 'Accepted Host', phoneNumber: '5551110000' },
      { id: 'user-pending', fullName: 'Pending Invitee', phoneNumber: '5552220000' },
      { id: 'user-available', fullName: 'Available Member', phoneNumber: '5553330000' },
    ],
  }),
}));

const BASE_EVENT = makeEvent({
  id: 'ev1',
  slug: 'spring-potluck',
  title: 'Spring Potluck',
  startDatetime: new Date('2099-06-01T18:00:00Z'),
  rsvpEnabled: false,
  attendingCount: 0,
  createdById: 'user-creator',
  createdByName: 'Alice',
  coHostIds: ['user-creator', 'user-accepted'],
  guests: [],
  pendingCohostInvites: [
    {
      id: 'inv1',
      userId: 'user-pending',
      userName: 'Pending Invitee',
      userPhotoUrl: '',
      invitedAt: new Date(),
    },
  ],
});

describe('AddCoHostDialog', () => {
  it('excludes members with a pending cohost invite from search results', () => {
    render(<AddCoHostDialog event={BASE_EVENT} open onClose={() => {}} />);

    fireEvent.change(screen.getByLabelText('search members'), { target: { value: 'me' } });

    expect(screen.getByText('Available Member')).toBeInTheDocument();
    expect(screen.queryByText('Pending Invitee')).not.toBeInTheDocument();
    expect(screen.queryByText('Accepted Host')).not.toBeInTheDocument();
  });

  it('resends pending invitees so adding a co-host does not rescind them', async () => {
    updateMutateAsync.mockClear();
    updateMutateAsync.mockResolvedValue(undefined);
    render(<AddCoHostDialog event={BASE_EVENT} open onClose={() => {}} />);

    fireEvent.change(screen.getByLabelText('search members'), { target: { value: 'me' } });
    fireEvent.click(screen.getByText('Available Member'));
    fireEvent.click(screen.getByRole('button', { name: 'add 1' }));

    await vi.waitFor(() => {
      expect(updateMutateAsync).toHaveBeenCalledTimes(1);
    });
    const sent = updateMutateAsync.mock.calls[0]?.[0] as { coHostIds: string[] };
    expect([...sent.coHostIds].sort()).toEqual([
      'user-accepted',
      'user-available',
      'user-creator',
      'user-pending',
    ]);
  });
});
