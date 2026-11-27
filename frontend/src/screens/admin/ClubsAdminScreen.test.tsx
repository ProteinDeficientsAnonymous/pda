import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Club } from '@/api/clubs';
import type { MemberSearchResult } from '@/api/userSearch';

import ClubsAdminScreen from './ClubsAdminScreen';

const create = vi.fn();
const update = vi.fn();
const remove = vi.fn();
const setReps = vi.fn<(clubId: string, ids: string[]) => Promise<unknown>>();
let clubs: Club[] = [];
let reps = new Map<string, MemberSearchResult[]>();
let repsStatus: 'success' | 'pending' | 'error' | 'stale-error' = 'success';
let searchResults: MemberSearchResult[] = [];

vi.mock('@/api/clubs', () => ({
  useClubs: () => ({ data: clubs, isPending: false, isError: false }),
  useCreateClub: () => ({ mutateAsync: create, isPending: false }),
  useUpdateClub: () => ({ mutateAsync: update, isPending: false }),
  useDeleteClub: () => ({ mutateAsync: remove, isPending: false }),
  useClubReps: () => ({
    data: repsStatus === 'success' || repsStatus === 'stale-error' ? reps : undefined,
    isPending: repsStatus === 'pending',
    isError: repsStatus === 'error' || repsStatus === 'stale-error',
    isSuccess: repsStatus === 'success',
  }),
  useSetClubReps: (clubId: string) => ({
    mutateAsync: ({ userIds, forClubId }: { userIds: string[]; forClubId?: string }) =>
      setReps(forClubId ?? clubId, userIds),
    isPending: false,
  }),
}));

vi.mock('@/api/userSearch', () => ({
  useUserSearch: () => ({ data: searchResults }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  create.mockResolvedValue({});
  update.mockResolvedValue({});
  remove.mockResolvedValue(undefined);
  setReps.mockResolvedValue({});
  repsStatus = 'success';
  searchResults = [{ id: 'u9', fullName: 'Cy Doe', phoneNumber: '+15551230000' }];
  reps = new Map([
    [
      'c1',
      [
        { id: 'u1', fullName: 'Ada', phoneNumber: '+15551230001' },
        { id: 'u2', fullName: 'Bo', phoneNumber: '+15551230002' },
      ],
    ],
  ]);
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

  it("shows each club's reps", () => {
    render(<ClubsAdminScreen />);
    expect(screen.getByText('reps: ada, bo')).toBeInTheDocument();
    expect(screen.getByText('no reps yet')).toBeInTheDocument();
  });

  it('saves picked reps when editing a club', async () => {
    const user = userEvent.setup();
    render(<ClubsAdminScreen />);
    await user.click(screen.getByRole('button', { name: 'edit book club' }));
    await user.type(screen.getByLabelText('reps'), 'cy');
    await user.click(await screen.findByRole('button', { name: /Cy Doe/ }));
    await user.click(screen.getByRole('button', { name: 'save' }));
    await waitFor(() => {
      expect(setReps).toHaveBeenCalledWith('c2', ['u9']);
    });
  });

  it('waits for reps to load before editing a club', async () => {
    repsStatus = 'pending';
    const user = userEvent.setup();
    render(<ClubsAdminScreen />);
    await user.click(screen.getByRole('button', { name: 'edit dog club' }));
    expect(screen.getByText('loading reps…')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'save' })).not.toBeInTheDocument();
  });

  it('shows an error and no save when reps fail to load', async () => {
    repsStatus = 'error';
    const user = userEvent.setup();
    render(<ClubsAdminScreen />);
    await user.click(screen.getByRole('button', { name: 'edit dog club' }));
    expect(screen.getByRole('alert')).toHaveTextContent("couldn't load reps — try again");
    expect(screen.queryByRole('button', { name: 'save' })).not.toBeInTheDocument();
  });

  it('keeps the form up when a refetch fails but reps data is present', async () => {
    repsStatus = 'stale-error';
    const user = userEvent.setup();
    render(<ClubsAdminScreen />);
    await user.click(screen.getByRole('button', { name: 'edit dog club' }));
    expect(screen.getByRole('button', { name: 'save' })).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows no rep line while reps are pending', () => {
    repsStatus = 'pending';
    render(<ClubsAdminScreen />);
    expect(screen.queryByText('no reps yet')).not.toBeInTheDocument();
  });

  it('does not touch reps when they are unchanged', async () => {
    const user = userEvent.setup();
    render(<ClubsAdminScreen />);
    await user.click(screen.getByRole('button', { name: 'edit dog club' }));
    await user.click(screen.getByRole('button', { name: 'save' }));
    await waitFor(() => {
      expect(update).toHaveBeenCalled();
    });
    expect(setReps).not.toHaveBeenCalled();
  });

  it('sets reps on the new club after creating it', async () => {
    create.mockResolvedValue({ id: 'new1', name: 'chess club', requirements: '' });
    const user = userEvent.setup();
    render(<ClubsAdminScreen />);
    await user.click(screen.getByRole('button', { name: 'add club' }));
    await user.type(screen.getByLabelText('name'), 'chess club');
    await user.type(screen.getByLabelText('reps'), 'cy');
    await user.click(await screen.findByRole('button', { name: /Cy Doe/ }));
    await user.click(screen.getByRole('button', { name: 'save' }));
    await waitFor(() => {
      expect(setReps).toHaveBeenCalledWith('new1', ['u9']);
    });
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
