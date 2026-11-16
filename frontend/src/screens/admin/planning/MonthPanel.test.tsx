import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { Assignment, PlannerColumn, PlanningGrid } from '@/api/planning';
import { makeSlot } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import { MonthPanel } from './MonthPanel';

const slot = makeSlot({ id: 's1', label: 'january', month: 1, order: 1 });

function planner(userId: string, overrides: Partial<PlannerColumn> = {}): PlannerColumn {
  return {
    userId,
    name: userId,
    isPlanner: true,
    hasEmail: true,
    submitted: true,
    biannualInterest: null,
    monthlyCount: 2,
    availableSlotIds: ['s1'],
    ...overrides,
  };
}

const on = (userId: string, status: Assignment['status']): Assignment => ({
  id: `a-${userId}`,
  slotId: 's1',
  userId,
  status,
});

function makeGrid(assignments: Assignment[], overrides: Partial<PlanningGrid> = {}): PlanningGrid {
  return {
    year: 2999,
    slots: [slot],
    planners: [planner('ada'), planner('bo'), planner('cy'), planner('dee')],
    assignments,
    ...overrides,
  };
}

function renderPanel(grid: PlanningGrid, { busy = false, onClose = vi.fn(), act = vi.fn() } = {}) {
  renderWithProviders(
    <MonthPanel
      grid={grid}
      slotId="s1"
      today={new Date(2026, 10, 15)}
      act={act}
      busy={busy}
      onClose={onClose}
    />,
  );
  return { act, onClose };
}

const row = (name: string) => screen.getByText(name).closest('li') as HTMLElement;

describe('MonthPanel', () => {
  it.each([
    [[on('ada', 'committed')], 2999, 'covered'],
    [[on('ada', 'proposed')], 2999, 'waiting'],
    [[on('ada', 'draft')], 2999, 'not sent yet'],
    [[], 2999, 'needs a planner'],
    [[], 2000, 'past'],
  ] as const)('tags %j in %i as %s', (assignments, year, tag) => {
    renderPanel(makeGrid([...assignments], { year }));
    expect(screen.getByRole('heading', { name: 'january' })).toBeInTheDocument();
    expect(screen.getAllByText(tag)[0]).toBeInTheDocument();
  });

  it('offers create event once someone is in', () => {
    renderPanel(makeGrid([on('ada', 'committed')]));
    expect(screen.getByRole('link', { name: 'create event' })).toBeInTheDocument();
  });

  it('proposes a free planner', async () => {
    const grid = makeGrid([]);
    const { act } = renderPanel(grid);
    expect(within(row('ada')).getByText('0 of 2 monthlies taken')).toBeInTheDocument();
    await userEvent.click(within(row('ada')).getByRole('button', { name: 'propose ada' }));
    expect(act).toHaveBeenCalledWith(slot, grid.planners[0], 'available', undefined);
  });

  it('labels each assignment and its action', () => {
    renderPanel(
      makeGrid([
        on('ada', 'draft'),
        on('bo', 'declined'),
        on('cy', 'proposed'),
        on('dee', 'committed'),
      ]),
    );
    expect(within(row('ada')).getByText('not sent yet')).toBeInTheDocument();
    expect(within(row('ada')).getByRole('button', { name: 'undo ada' })).toBeInTheDocument();
    expect(within(row('bo')).getByRole('button', { name: 'propose again bo' })).toBeInTheDocument();
    expect(within(row('cy')).getByRole('button', { name: 'withdraw cy' })).toBeInTheDocument();
    expect(within(row('dee')).getByText('in')).toBeInTheDocument();
  });

  it('passes the assignment when withdrawing', async () => {
    const grid = makeGrid([on('ada', 'committed')]);
    const { act } = renderPanel(grid);
    await userEvent.click(within(row('ada')).getByRole('button', { name: 'withdraw ada' }));
    expect(act).toHaveBeenCalledWith(slot, grid.planners[0], 'committed', grid.assignments[0]);
  });

  it('disables every row button while busy', () => {
    renderPanel(makeGrid([on('ada', 'draft'), on('bo', 'declined')]), { busy: true });
    for (const r of screen.getAllByRole('listitem')) {
      expect(within(r).getByRole('button')).toBeDisabled();
    }
    expect(screen.getByRole('button', { name: 'close january' })).toBeEnabled();
  });

  it('links to the event once one exists', () => {
    const withEvent = makeSlot({
      id: 's1',
      label: 'january',
      month: 1,
      order: 1,
      eventId: 'e1',
      eventSlug: 'jan-potluck',
      eventStatus: 'active',
    });
    renderPanel(makeGrid([on('ada', 'committed')], { slots: [withEvent] }));
    expect(screen.getByRole('link', { name: 'view event' })).toBeInTheDocument();
  });

  it('closes', async () => {
    const { onClose } = renderPanel(makeGrid([]));
    await userEvent.click(screen.getByRole('button', { name: 'close january' }));
    expect(onClose).toHaveBeenCalled();
  });

  it('will not propose someone who is not a planner', () => {
    renderPanel(makeGrid([], { planners: [planner('ada', { isPlanner: false })] }));
    expect(within(row('ada')).getByRole('button', { name: 'propose ada' })).toBeDisabled();
  });
});
