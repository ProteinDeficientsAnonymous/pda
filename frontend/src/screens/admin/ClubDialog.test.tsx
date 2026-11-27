import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ClubDialog } from './ClubDialog';

const create = vi.fn();
let createPending = false;

vi.mock('@/api/clubs', () => ({
  useCreateClub: () => ({ mutateAsync: create, isPending: createPending }),
  useUpdateClub: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useClubReps: () => ({ data: new Map(), isPending: false, isError: false }),
  useSetClubReps: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/api/userSearch', () => ({
  useUserSearch: () => ({ data: [] }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  createPending = false;
});

describe('ClubDialog', () => {
  it('shows an error and stays open when saving fails', async () => {
    create.mockRejectedValueOnce(new Error('boom'));
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<ClubDialog open onClose={onClose} />);
    await user.type(screen.getByLabelText('name'), 'chess club');
    await user.click(screen.getByRole('button', { name: 'save' }));
    expect(await screen.findByRole('alert')).toHaveTextContent("couldn't save — try again");
    expect(onClose).not.toHaveBeenCalled();
  });

  it('shows saving while a save is in flight', () => {
    createPending = true;
    render(<ClubDialog open onClose={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'saving…' })).toBeDisabled();
  });
});
