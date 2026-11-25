import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type * as ClubsApi from '@/api/clubs';
import type { Club } from '@/api/clubs';
import { renderWithProviders } from '@/test/render';

import ClubsAdminScreen from './ClubsAdminScreen';

const remove = vi.fn();
let clubsState: { data: Club[]; isPending: boolean; isError: boolean };

vi.mock('@/api/clubs', async (importOriginal) => ({
  ...(await importOriginal<typeof ClubsApi>()),
  useClubs: () => clubsState,
  useDeleteClub: () => ({ mutateAsync: remove, isPending: false }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  clubsState = {
    data: [{ id: 'c1', name: 'dog club', requirements: '' }],
    isPending: false,
    isError: false,
  };
});

describe('ClubsAdminScreen states', () => {
  it('shows loading while clubs load', () => {
    clubsState = { data: [], isPending: true, isError: false };
    renderWithProviders(<ClubsAdminScreen />);
    expect(screen.getByText('loading…')).toBeInTheDocument();
  });

  it('shows an error when clubs fail to load', () => {
    clubsState = { data: [], isPending: false, isError: true };
    renderWithProviders(<ClubsAdminScreen />);
    expect(screen.getByRole('alert')).toHaveTextContent("couldn't load clubs");
  });

  it('shows the empty state when there are no clubs', () => {
    clubsState = { data: [], isPending: false, isError: false };
    renderWithProviders(<ClubsAdminScreen />);
    expect(screen.getByText('no clubs yet')).toBeInTheDocument();
  });

  it('shows an error when delete fails', async () => {
    remove.mockRejectedValueOnce(new Error('boom'));
    const user = userEvent.setup();
    renderWithProviders(<ClubsAdminScreen />);
    await user.click(screen.getByRole('button', { name: 'delete dog club' }));
    await user.click(screen.getByRole('button', { name: 'delete' }));
    expect(await screen.findByRole('alert')).toHaveTextContent("couldn't delete — try again");
  });
});
