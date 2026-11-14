import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { MySlot } from '@/api/planning';
import { renderWithProviders } from '@/test/render';

import { MySlots } from './MySlots';

const mine = (id: string, status: MySlot['status'], year = 2027): MySlot => ({
  assignmentId: id,
  status,
  year,
  slot: {
    id: `slot-${id}`,
    label: `label ${id}`,
    month: 1,
    kind: 'monthly',
    order: 1,
    eventId: null,
    eventSlug: null,
    eventStatus: null,
  },
  teammates: [],
});

let state: { isPending: boolean; isError: boolean; data: MySlot[] | undefined };
const commit = vi.fn();
const decline = vi.fn();
const toastError = vi.fn();

vi.mock('sonner', () => ({
  toast: {
    error: (m: string) => {
      toastError(m);
    },
  },
}));

vi.mock('@/api/planning', () => ({
  useMySlots: () => state,
  useCommit: () => ({ mutateAsync: commit, isPending: false }),
  useDecline: () => ({ mutateAsync: decline, isPending: false }),
}));

beforeEach(() => {
  state = { isPending: false, isError: false, data: [] };
  commit.mockReset().mockResolvedValue(undefined);
  decline.mockReset().mockResolvedValue(undefined);
  toastError.mockReset();
});

describe('MySlots', () => {
  it('shows the empty state', () => {
    renderWithProviders(<MySlots />);
    expect(screen.getByText('nothing assigned yet 🌿')).toBeInTheDocument();
  });

  it('commits a proposed slot with "i\'m in"', async () => {
    state.data = [mine('a1', 'proposed')];
    renderWithProviders(<MySlots />);
    const section = screen.getByRole('region', { name: 'waiting on you' });
    await userEvent.click(within(section).getByRole('button', { name: "i'm in" }));
    expect(commit).toHaveBeenCalledWith('a1');
  });

  it('declines a proposed slot without confirming', async () => {
    state.data = [mine('a1', 'proposed')];
    renderWithProviders(<MySlots />);
    await userEvent.click(screen.getByRole('button', { name: "can't do it" }));
    expect(decline).toHaveBeenCalledWith('a1');
  });

  it('prefixes the year only when several years are present', () => {
    state.data = [mine('a1', 'proposed'), mine('a2', 'proposed', 2028)];
    const { unmount } = renderWithProviders(<MySlots />);
    expect(screen.getByText('2027 · label a1')).toBeInTheDocument();
    expect(screen.getByText('2028 · label a2')).toBeInTheDocument();
    unmount();
    state.data = [mine('a1', 'proposed')];
    renderWithProviders(<MySlots />);
    expect(screen.getByText('label a1')).toBeInTheDocument();
  });

  it('toasts when responding fails', async () => {
    commit.mockRejectedValue(new Error('nope'));
    state.data = [mine('a1', 'proposed')];
    renderWithProviders(<MySlots />);
    await userEvent.click(screen.getByRole('button', { name: "i'm in" }));
    expect(toastError).toHaveBeenCalledWith("couldn't save your response — try again");
  });

  it('shows an error state', () => {
    state = { isPending: false, isError: true, data: undefined };
    renderWithProviders(<MySlots />);
    expect(screen.getByText("couldn't load your slots — try refreshing")).toBeInTheDocument();
  });
});
