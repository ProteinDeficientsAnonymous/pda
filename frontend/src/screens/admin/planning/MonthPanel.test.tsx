import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { Assignment, PlannerColumn, PlanningGrid } from '@/api/planning';
import { makeAssignment, makePlanner, makePlanningGrid, makeSlot } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import { MonthPanel } from './MonthPanel';

const slot = makeSlot({ id: 's1', label: 'january', month: 1, order: 1 });

const planner = (userId: string, overrides: Partial<PlannerColumn> = {}) =>
  makePlanner({ userId, name: userId, monthlyCount: 2, availableSlotIds: ['s1'], ...overrides });

const on = (userId: string, status: Assignment['status']) =>
  makeAssignment({ id: `a-${userId}`, userId, status });

const makeGrid = (assignments: Assignment[], overrides: Partial<PlanningGrid> = {}) =>
  makePlanningGrid({
    slots: [slot],
    planners: [planner('ada'), planner('bo'), planner('cy'), planner('dee')],
    assignments,
    ...overrides,
  });

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

const addButton = () => screen.getByRole('button', { name: /^add someone/ });

const openAdd = () => userEvent.click(addButton());

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
    await openAdd();
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
    expect(within(row('dee')).getByRole('button', { name: 'withdraw dee' })).toBeInTheDocument();
  });

  it('lists committed planners under planning, apart from asked', () => {
    renderPanel(makeGrid([on('ada', 'committed'), on('bo', 'proposed')]));
    const [planning, asked] = screen.getAllByRole('list') as [HTMLElement, HTMLElement];
    expect(screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)).toEqual([
      'planning',
      'asked',
    ]);
    expect(within(planning).getByText('ada')).toBeInTheDocument();
    expect(within(planning).queryByText('in')).not.toBeInTheDocument();
    expect(within(asked).getByText('bo')).toBeInTheDocument();
  });

  it('labels a sent proposal', () => {
    renderPanel(makeGrid([on('ada', 'proposed')]));
    expect(within(row('ada')).getByText('sent')).toBeInTheDocument();
  });

  it('keeps a proposal as sent after its month has started', () => {
    renderPanel(makeGrid([on('ada', 'proposed')], { year: 2000 }));
    expect(within(row('ada')).getByText('sent')).toBeInTheDocument();
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

  it('will not propose someone who is not a planner', async () => {
    renderPanel(makeGrid([], { planners: [planner('ada', { isPlanner: false })] }));
    await openAdd();
    expect(within(row('ada')).getByRole('button', { name: 'propose ada' })).toBeDisabled();
    expect(within(row('ada')).getByText('no longer a planner')).toBeInTheDocument();
  });

  describe('add someone', () => {
    const gridWithOthers = () =>
      makeGrid([on('ada', 'committed')], {
        planners: [
          planner('ada'),
          planner('bo'),
          planner('cy'),
          planner('dan', { availableSlotIds: [] }),
          planner('mo', { submitted: false, availableSlotIds: [] }),
        ],
      });

    it('hides everyone not on the slot and counts who is free', () => {
      renderPanel(gridWithOthers());
      expect(addButton()).toHaveTextContent('add someone · 2 free');
      expect(addButton()).toHaveAttribute('aria-expanded', 'false');
      for (const name of ['bo', 'cy', 'dan', 'mo']) {
        expect(screen.queryByText(name)).not.toBeInTheDocument();
      }
    });

    it('shows free then no form once expanded, never who is not free', async () => {
      renderPanel(gridWithOthers());
      await openAdd();
      expect(screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)).toEqual([
        'planning',
        'free',
        'no form',
      ]);
      expect(screen.queryByText('dan')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'hide' })).toHaveAttribute('aria-expanded', 'true');
    });

    it('proposes someone with no form', async () => {
      const grid = gridWithOthers();
      const { act } = renderPanel(grid);
      await openAdd();
      await userEvent.click(within(row('mo')).getByRole('button', { name: 'propose mo' }));
      expect(act).toHaveBeenCalledWith(slot, grid.planners[4], 'blank', undefined);
    });

    it('drops the count when nobody is free', () => {
      renderPanel(
        makeGrid([], { planners: [planner('mo', { submitted: false, availableSlotIds: [] })] }),
      );
      expect(addButton()).toHaveTextContent(/^add someone$/);
    });

    it('is gone when nobody is left to add', () => {
      renderPanel(
        makeGrid([on('ada', 'committed')], {
          planners: [planner('ada'), planner('ex', { isPlanner: false, availableSlotIds: [] })],
        }),
      );
      expect(screen.queryByRole('button', { name: /add someone/ })).not.toBeInTheDocument();
    });
  });

  it('shows biannual interest only on an extra slot', async () => {
    const planners = [planner('ada', { biannualInterest: 'maybe' })];
    renderPanel(makeGrid([], { planners, slots: [{ ...slot, kind: 'biannual' }] }));
    await openAdd();
    expect(within(row('ada')).getByText('biannual: maybe')).toBeInTheDocument();
  });

  it('hides biannual interest on a monthly slot', async () => {
    renderPanel(makeGrid([], { planners: [planner('ada', { biannualInterest: 'maybe' })] }));
    await openAdd();
    expect(screen.queryByText('biannual: maybe')).not.toBeInTheDocument();
  });

  it('flags planners with no email', async () => {
    renderPanel(makeGrid([], { planners: [planner('ada', { hasEmail: false })] }));
    await openAdd();
    expect(within(row('ada')).getByText('no email')).toBeInTheDocument();
  });
});
