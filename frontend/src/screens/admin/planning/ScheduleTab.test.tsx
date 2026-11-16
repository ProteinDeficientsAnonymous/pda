import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { PlanningGrid } from '@/api/planning';
import { makeSlot } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import { ScheduleTab } from './ScheduleTab';

const grid: PlanningGrid = {
  year: 2999,
  slots: [makeSlot({ id: 's1', label: 'january', month: 1, order: 1 })],
  planners: [
    {
      userId: 'u1',
      name: 'ada',
      isPlanner: true,
      hasEmail: true,
      submitted: true,
      biannualInterest: null,
      monthlyCount: 1,
      availableSlotIds: ['s1'],
    },
  ],
  assignments: [],
};

let shown = grid;
let status = { isPending: false, isError: false };

const mutation = { mutateAsync: vi.fn(), isPending: false };

vi.mock('@/api/planning', () => ({
  usePlanningGrid: () => ({
    ...status,
    data: status.isPending || status.isError ? undefined : shown,
  }),
  usePropose: () => mutation,
  useWithdraw: () => mutation,
  useSendProposals: () => mutation,
}));

describe('ScheduleTab', () => {
  beforeEach(() => {
    shown = grid;
    status = { isPending: false, isError: false };
  });

  it('toggles the open month on repeat taps', async () => {
    renderWithProviders(<ScheduleTab year={2999} />);
    const january = screen.getByRole('button', { name: 'january' });
    await userEvent.click(january);
    expect(january).toHaveAttribute('aria-pressed', 'true');
    await userEvent.click(january);
    expect(january).toHaveAttribute('aria-pressed', 'false');
  });

  it('opens the month panel and closes it from the panel', async () => {
    renderWithProviders(<ScheduleTab year={2999} />);
    expect(screen.queryByRole('heading', { name: 'january' })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'january' }));
    expect(screen.getByRole('heading', { name: 'january' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'close january' }));
    expect(screen.queryByRole('heading', { name: 'january' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'january' })).toHaveFocus();
  });

  it('collapses add someone when another month opens', async () => {
    shown = {
      ...grid,
      slots: [...grid.slots, makeSlot({ id: 's2', label: 'february', month: 2, order: 2 })],
    };
    renderWithProviders(<ScheduleTab year={2999} />);
    await userEvent.click(screen.getByRole('button', { name: 'february' }));
    await userEvent.click(screen.getByRole('button', { name: 'add someone' }));
    expect(screen.getByRole('button', { name: 'hide' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'january' }));
    await userEvent.click(screen.getByRole('button', { name: 'february' }));
    expect(screen.getByRole('button', { name: 'add someone' })).toHaveAttribute(
      'aria-expanded',
      'false',
    );
  });

  it('shows the send bar while drafts wait', () => {
    shown = { ...grid, assignments: [{ id: 'a1', slotId: 's1', userId: 'u1', status: 'draft' }] };
    renderWithProviders(<ScheduleTab year={2999} />);
    expect(screen.getByText('1 not sent yet')).toBeInTheDocument();
  });

  it.each(['committed', 'proposed'] as const)(
    'confirms before withdrawing a %s tile',
    async (status) => {
      shown = { ...grid, assignments: [{ id: 'a1', slotId: 's1', userId: 'u1', status }] };
      renderWithProviders(<ScheduleTab year={2999} />);
      await userEvent.click(screen.getByRole('button', { name: 'withdraw ada from january' }));
      expect(screen.getByText('withdraw ada from january?')).toBeInTheDocument();
      expect(mutation.mutateAsync).not.toHaveBeenCalled();
    },
  );

  it('proposes straight from an available tile', async () => {
    renderWithProviders(<ScheduleTab year={2999} />);
    await userEvent.click(screen.getByRole('button', { name: 'propose ada for january' }));
    expect(mutation.mutateAsync).toHaveBeenCalledWith({ slotId: 's1', userId: 'u1' });
  });

  it('disables the tiles while a change is pending', () => {
    mutation.isPending = true;
    renderWithProviders(<ScheduleTab year={2999} />);
    expect(screen.getByRole('button', { name: 'propose ada for january' })).toBeDisabled();
  });

  it('shows the summary pills with the grid', () => {
    renderWithProviders(<ScheduleTab year={2999} />);
    expect(screen.getByText('need a planner').parentElement).toHaveTextContent('1 need a planner');
  });

  it('says so when there are no planners yet', () => {
    shown = { ...grid, planners: [] };
    renderWithProviders(<ScheduleTab year={2999} />);
    expect(screen.getByText('no planners yet 🌿')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'january' })).not.toBeInTheDocument();
    expect(screen.queryByText('need a planner')).not.toBeInTheDocument();
  });

  it('shows loading while the grid loads', () => {
    status = { isPending: true, isError: false };
    renderWithProviders(<ScheduleTab year={2999} />);
    expect(screen.getByText('loading…')).toBeInTheDocument();
  });

  it('shows an error when the grid fails to load', () => {
    status = { isPending: false, isError: true };
    renderWithProviders(<ScheduleTab year={2999} />);
    expect(screen.getByRole('alert')).toHaveTextContent(
      "couldn't load the planning grid — try refreshing",
    );
  });
});
