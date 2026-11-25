import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Club } from '@/api/clubs';

import ClubsAdminScreen from './ClubsAdminScreen';

const create = vi.fn();
const update = vi.fn();
const remove = vi.fn();
let clubs: Club[] = [];

vi.mock('@/api/clubs', () => ({
  useClubs: () => ({ data: clubs, isPending: false, isError: false }),
  useCreateClub: () => ({ mutateAsync: create, isPending: false }),
  useUpdateClub: () => ({ mutateAsync: update, isPending: false }),
  useDeleteClub: () => ({ mutateAsync: remove, isPending: false }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  create.mockResolvedValue({});
  update.mockResolvedValue({});
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

  it('adds a club', async () => {
    const user = userEvent.setup();
    render(<ClubsAdminScreen />);
    await user.click(screen.getByRole('button', { name: 'add club' }));
    await user.type(screen.getByLabelText('name'), ' chess club ');
    await user.type(screen.getByLabelText('requirements'), 'any level');
    await user.click(screen.getByRole('button', { name: 'save' }));
    await waitFor(() => {
      expect(create).toHaveBeenCalledWith({ name: 'chess club', requirements: 'any level' });
    });
  });

  it('shows an error when the name is blank', async () => {
    const user = userEvent.setup();
    render(<ClubsAdminScreen />);
    await user.click(screen.getByRole('button', { name: 'add club' }));
    await user.click(screen.getByRole('button', { name: 'save' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('name required');
    expect(create).not.toHaveBeenCalled();
  });

  it('edits a club', async () => {
    const user = userEvent.setup();
    render(<ClubsAdminScreen />);
    await user.click(screen.getByRole('button', { name: 'edit book club' }));
    const name = screen.getByLabelText('name');
    await user.clear(name);
    await user.type(name, 'reading club');
    await user.click(screen.getByRole('button', { name: 'save' }));
    await waitFor(() => {
      expect(update).toHaveBeenCalledWith({ name: 'reading club', requirements: '' });
    });
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
