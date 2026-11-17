import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { MySlot } from '@/api/planning';
import { makeSlot } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import { MySlots } from './MySlots';

const mine = (id: string, status: MySlot['status'], year = 2027): MySlot => ({
  assignmentId: id,
  status,
  year,
  slot: makeSlot({ id: `slot-${id}`, label: `label ${id}`, month: 1, order: 1 }),
  teammates: [],
  checklistDoneIds: [],
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

vi.mock('./SlotChecklist', () => ({
  SlotChecklist: ({ label }: { label: string }) => <div>checklist for {label}</div>,
}));

beforeEach(() => {
  state = { isPending: false, isError: false, data: [] };
  commit.mockReset().mockResolvedValue(undefined);
  decline.mockReset().mockResolvedValue(undefined);
  toastError.mockReset();
});

describe('MySlots', () => {
  it('shows the checklist only on slots the planner committed to', () => {
    state.data = [mine('a1', 'proposed'), mine('a2', 'committed')];
    renderWithProviders(<MySlots />);
    expect(screen.getByText('checklist for label a2')).toBeInTheDocument();
    expect(screen.queryByText('checklist for label a1')).not.toBeInTheDocument();
  });

  it('shows the empty state', () => {
    renderWithProviders(<MySlots />);
    expect(
      screen.getByText('nothing yet — add your availability so you can be proposed some months 🌿'),
    ).toBeInTheDocument();
  });

  it('commits a proposed slot with "i\'m in"', async () => {
    state.data = [mine('a1', 'proposed')];
    renderWithProviders(<MySlots />);
    const section = screen.getByRole('region', { name: 'waiting on you' });
    await userEvent.click(within(section).getByRole('button', { name: "i'm in for label a1" }));
    expect(commit).toHaveBeenCalledWith('a1');
  });

  it('declines a proposed slot without confirming', async () => {
    state.data = [mine('a1', 'proposed')];
    renderWithProviders(<MySlots />);
    await userEvent.click(screen.getByRole('button', { name: "can't do label a1" }));
    expect(decline).toHaveBeenCalledWith('a1');
  });

  it('lists committed slots with teammates and an event link', () => {
    const row = mine('a2', 'committed');
    state.data = [
      {
        ...row,
        teammates: [
          { name: 'bea', status: 'committed' },
          { name: 'cy', status: 'proposed' },
        ],
        slot: { ...row.slot, eventId: 'e1', eventSlug: 'jan-potluck', eventStatus: 'draft' },
      },
    ];
    renderWithProviders(<MySlots />);
    const section = screen.getByRole('region', { name: "events you're planning" });
    expect(within(section).getByText('label a2')).toBeInTheDocument();
    expect(within(section).getByText('with bea (committed), cy (proposed)')).toBeInTheDocument();
    expect(within(section).getByRole('link', { name: 'view event' })).toHaveAttribute(
      'href',
      '/events/jan-potluck',
    );
    expect(within(section).getByText(/draft ·/)).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'waiting on you' })).not.toBeInTheDocument();
  });

  it('offers create event only on committed rows', () => {
    state.data = [mine('a1', 'proposed'), mine('a2', 'committed')];
    renderWithProviders(<MySlots />);
    const waiting = screen.getByRole('region', { name: 'waiting on you' });
    expect(within(waiting).queryByRole('link')).not.toBeInTheDocument();
    const yours = screen.getByRole('region', { name: "events you're planning" });
    expect(within(yours).getByRole('link', { name: 'create event' })).toHaveAttribute(
      'href',
      '/events/add?planningSlot=slot-a2&year=2027',
    );
  });

  it('says when nobody else is on the slot yet', () => {
    state.data = [mine('a2', 'committed')];
    renderWithProviders(<MySlots />);
    expect(screen.getByText('just you so far')).toBeInTheDocument();
  });

  it('puts create event next to back out', () => {
    state.data = [mine('a2', 'committed')];
    renderWithProviders(<MySlots />);
    const create = screen.getByRole('link', { name: 'create event' });
    const backOut = screen.getByRole('button', { name: 'back out of label a2' });
    expect(create.parentElement).toBe(backOut.parentElement);
  });

  it('backs out only after confirming', async () => {
    state.data = [mine('a2', 'committed')];
    renderWithProviders(<MySlots />);
    await userEvent.click(screen.getByRole('button', { name: 'back out of label a2' }));
    expect(
      screen.getByText("back out of label a2? no worries — we'll pass it along"),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'cancel' }));
    expect(decline).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'back out of label a2' }));
    await userEvent.click(screen.getByRole('button', { name: 'yes, back out' }));
    expect(decline).toHaveBeenCalledWith('a2');
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
    await userEvent.click(screen.getByRole('button', { name: "i'm in for label a1" }));
    expect(toastError).toHaveBeenCalledWith("couldn't save your response — try again");
  });

  it('shows an error state', () => {
    state = { isPending: false, isError: true, data: undefined };
    renderWithProviders(<MySlots />);
    expect(screen.getByText("couldn't load your events — try refreshing")).toBeInTheDocument();
  });
});
