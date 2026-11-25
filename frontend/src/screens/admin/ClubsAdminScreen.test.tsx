import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Club } from '@/api/clubs';

import ClubsAdminScreen from './ClubsAdminScreen';

const remove = vi.fn();
let clubs: Club[] = [];

vi.mock('@/api/clubs', () => ({
  useClubs: () => ({ data: clubs, isPending: false, isError: false }),
  useDeleteClub: () => ({ mutateAsync: remove, isPending: false }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  remove.mockResolvedValue(undefined);
  clubs = [
    { id: 'c1', name: 'dog club', requirements: 'must be dog parent // guardian' },
    { id: 'c2', name: 'book club', requirements: '' },
  ];
});

describe('ClubsAdminScreen', () => {
  it('lists clubs with their requirements', () => {
    render(<ClubsAdminScreen />);
    expect(screen.getByText('dog club')).toBeInTheDocument();
    expect(screen.getByText('must be dog parent // guardian')).toBeInTheDocument();
    expect(screen.getByText('book club')).toBeInTheDocument();
  });

  it('deletes a club after confirming', async () => {
    const user = userEvent.setup();
    render(<ClubsAdminScreen />);
    await user.click(screen.getByRole('button', { name: 'delete dog club' }));
    expect(screen.getByText(/lose their club link/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'delete' }));
    await waitFor(() => {
      expect(remove).toHaveBeenCalledWith('c1');
    });
  });
});
