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

let shown: PlanningGrid | undefined = grid;

const mutation = { mutateAsync: vi.fn(), isPending: false };

vi.mock('@/api/planning', () => ({
  usePlanningGrid: () => ({ isPending: false, isError: false, data: shown }),
  usePropose: () => mutation,
  useWithdraw: () => mutation,
  useSendProposals: () => mutation,
}));

vi.mock('./PlanningGrid', () => ({
  PlanningGrid: ({ year }: { year: number }) => <div>old table for {year}</div>,
}));

describe('ScheduleTab', () => {
  beforeEach(() => {
    shown = grid;
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

  it('keeps the old table below the new grid', () => {
    renderWithProviders(<ScheduleTab year={2999} />);
    const january = screen.getByRole('button', { name: 'january' });
    const old = screen.getByText('old table for 2999');
    expect(january.compareDocumentPosition(old) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('shows the send bar while drafts wait', () => {
    shown = { ...grid, assignments: [{ id: 'a1', slotId: 's1', userId: 'u1', status: 'draft' }] };
    renderWithProviders(<ScheduleTab year={2999} />);
    expect(screen.getByText('1 not sent yet')).toBeInTheDocument();
  });

  it('shows the summary pills with the grid', () => {
    renderWithProviders(<ScheduleTab year={2999} />);
    expect(screen.getByText('need a planner').parentElement).toHaveTextContent('1 need a planner');
  });

  it('renders only the old table while the grid loads', () => {
    shown = undefined;
    renderWithProviders(<ScheduleTab year={2999} />);
    expect(screen.queryByText(/not sent yet/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'january' })).not.toBeInTheDocument();
    expect(screen.getByText('old table for 2999')).toBeInTheDocument();
  });

  it('skips the grid without planners', () => {
    shown = { ...grid, planners: [] };
    renderWithProviders(<ScheduleTab year={2999} />);
    expect(screen.queryByRole('button', { name: 'january' })).not.toBeInTheDocument();
    expect(screen.queryByText('need a planner')).not.toBeInTheDocument();
    expect(screen.getByText('old table for 2999')).toBeInTheDocument();
  });
});
