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

  it('offers no create event while the slot is only proposed', () => {
    renderPanel(makeGrid([on('ada', 'proposed')]));
    expect(screen.queryByRole('link', { name: 'create event' })).not.toBeInTheDocument();
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
    expect(screen.getByRole('heading', { name: 'asked' })).toBeInTheDocument();
    expect(within(row('ada')).getByText('not sent yet')).toBeInTheDocument();
    expect(within(row('ada')).getByRole('button', { name: 'undo ada' })).toBeInTheDocument();
    expect(within(row('bo')).getByRole('button', { name: 'propose again bo' })).toBeInTheDocument();
    expect(within(row('cy')).getByRole('button', { name: 'withdraw cy' })).toBeInTheDocument();
    expect(within(row('dee')).getByText('in')).toBeInTheDocument();
  });

  it('labels a sent proposal', () => {
    renderPanel(makeGrid([on('ada', 'proposed')]));
    expect(within(row('ada')).getByText('sent')).toBeInTheDocument();
  });

  it('offers withdraw when a started month is awaiting an answer', () => {
    renderPanel(makeGrid([on('ada', 'proposed')], { year: 2000 }));
    expect(within(row('ada')).getByText('awaiting answer')).toBeInTheDocument();
    expect(within(row('ada')).getByRole('button', { name: 'withdraw ada' })).toBeInTheDocument();
  });

  it('proposes a decliner again', async () => {
    const grid = makeGrid([on('bo', 'declined')]);
    const { act } = renderPanel(grid);
    await userEvent.click(within(row('bo')).getByRole('button', { name: 'propose again bo' }));
    expect(act).toHaveBeenCalledWith(slot, grid.planners[1], 'declined', grid.assignments[0]);
  });

  it('will not propose a decliner who is no longer a planner', () => {
    renderPanel(
      makeGrid([on('bo', 'declined'), on('cy', 'committed')], {
        planners: [planner('bo', { isPlanner: false }), planner('cy', { isPlanner: false })],
      }),
    );
    expect(within(row('bo')).getByRole('button', { name: 'propose again bo' })).toBeDisabled();
    expect(within(row('cy')).getByRole('button', { name: 'withdraw cy' })).toBeEnabled();
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
    expect(within(row('ada')).getByText('no longer a planner')).toBeInTheDocument();
  });

  describe('everyone else', () => {
    const gridWithOthers = (slotOverrides: Partial<PlanningGrid['slots'][number]> = {}) =>
      makeGrid([], {
        slots: [{ ...slot, ...slotOverrides }],
        planners: [
          planner('ada'),
          planner('dan', { availableSlotIds: [] }),
          planner('duncan', { availableSlotIds: [] }),
          planner('mo', { submitted: false, availableSlotIds: [] }),
          planner('jo', { submitted: false, availableSlotIds: [] }),
        ],
      });

    it('lists them on muted lines', () => {
      renderPanel(gridWithOthers());
      expect(screen.getByText('not free · dan, duncan')).toBeInTheDocument();
      expect(screen.getByText('no form · mo, jo')).toBeInTheDocument();
    });

    it('proposes someone who is not free after add someone', async () => {
      const grid = gridWithOthers();
      const { act } = renderPanel(grid);
      const add = screen.getByRole('button', { name: 'add someone' });
      expect(add).toHaveAttribute('aria-expanded', 'false');
      await userEvent.click(add);
      expect(add).toHaveAttribute('aria-expanded', 'true');
      await userEvent.click(within(row('dan')).getByRole('button', { name: 'propose dan' }));
      expect(act).toHaveBeenCalledWith(slot, grid.planners[1], 'blank', undefined);
    });

    it('leaves ex-planners out of add someone', async () => {
      renderPanel(
        makeGrid([], {
          planners: [planner('ada'), planner('ex', { isPlanner: false, availableSlotIds: [] })],
        }),
      );
      expect(screen.queryByRole('button', { name: 'add someone' })).not.toBeInTheDocument();
      expect(screen.queryByText(/not free/)).not.toBeInTheDocument();
    });

    it('splits not free from no form once expanded and offers hide', async () => {
      renderPanel(gridWithOthers());
      await userEvent.click(screen.getByRole('button', { name: 'add someone' }));
      expect(screen.getByRole('heading', { name: 'not free' })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'no form' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'hide' })).toHaveAttribute('aria-expanded', 'true');
    });

    it('has no add someone when everyone is free', () => {
      renderPanel(makeGrid([]));
      expect(screen.queryByRole('button', { name: 'add someone' })).not.toBeInTheDocument();
    });
  });

  it('shows biannual interest only on an extra slot', () => {
    const planners = [planner('ada', { biannualInterest: 'maybe' })];
    renderPanel(makeGrid([], { planners, slots: [{ ...slot, kind: 'biannual' }] }));
    expect(within(row('ada')).getByText('biannual: maybe')).toBeInTheDocument();
  });

  it('hides biannual interest on a monthly slot', () => {
    renderPanel(makeGrid([], { planners: [planner('ada', { biannualInterest: 'maybe' })] }));
    expect(screen.queryByText('biannual: maybe')).not.toBeInTheDocument();
  });

  it('flags planners with no email', () => {
    renderPanel(makeGrid([], { planners: [planner('ada', { hasEmail: false })] }));
    expect(within(row('ada')).getByText('no email')).toBeInTheDocument();
  });
});
