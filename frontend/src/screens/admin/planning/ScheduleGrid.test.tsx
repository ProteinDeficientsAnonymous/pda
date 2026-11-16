import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { PlannerColumn } from '@/api/planning';
import { makeAssignment, makePlanner, makePlanningGrid, makeSlot } from '@/test/fixtures';

import { ScheduleGrid } from './ScheduleGrid';

const planner = (userId: string, name: string, extra: Partial<PlannerColumn> = {}) =>
  makePlanner({ userId, name, biannualInterest: 'yes', monthlyCount: 2, ...extra });

const grid = makePlanningGrid({
  slots: [
    makeSlot({ id: 's3', label: 'spring biannual', month: 4, kind: 'biannual', order: 1 }),
    makeSlot({ id: 's1', label: 'january', month: 1, order: 1 }),
    makeSlot({ id: 's2', label: 'february', month: 2, order: 2 }),
  ],
  planners: [
    planner('u1', 'ada', { availableSlotIds: ['s1'] }),
    planner('u3', 'cy', { submitted: false, monthlyCount: 0, hasEmail: false }),
    planner('u2', 'bo', { isPlanner: false, monthlyCount: 1, biannualInterest: 'maybe' }),
  ],
  assignments: [
    makeAssignment({ userId: 'u2', status: 'committed' }),
    makeAssignment({ id: 'a2', slotId: 's2', userId: 'u2' }),
  ],
});

function renderGrid(overrides: Partial<Parameters<typeof ScheduleGrid>[0]> = {}) {
  const props = {
    grid,
    today: new Date(2999, 0, 1),
    openSlotId: null,
    onToggleSlot: vi.fn(),
    act: vi.fn().mockResolvedValue(undefined),
    busy: false,
    ...overrides,
  };
  const { container } = render(<ScheduleGrid {...props} />);
  return { ...props, container };
}

describe('ScheduleGrid', () => {
  it('scrolls inside its own relative wrapper', () => {
    const { container } = renderGrid();
    expect(container.querySelector('.overflow-x-auto')).toHaveClass(
      'relative',
      'overflow-y-hidden',
    );
  });

  it('sets the grid size vars, larger from md, on the wrapper around grid and key', () => {
    const { container } = renderGrid();
    expect(container.firstElementChild).toHaveClass(
      '[--pg-col:17px]',
      'md:[--pg-col:30px]',
      'md:[--pg-name:150px]',
      'md:[--pg-row:34px]',
      'md:[--pg-tile:24px]',
    );
  });

  it.each([
    [[true, false, true], 'r r 1px r r 1px r'],
    [[true, true], 'r r 1px r r'],
    [[false, false], 'r r 1px r r'],
  ])('draws the dividers for submitted %o as 1px rows', (flags, rows) => {
    const planners = flags.map((submitted, i) =>
      planner(`p${String(i)}`, `p${String(i)}`, { submitted }),
    );
    const { container } = renderGrid({ grid: { ...grid, planners } });
    expect(container.querySelector<HTMLElement>('.grid')?.style.gridTemplateRows).toBe(
      rows.replaceAll('r', 'var(--pg-row)'),
    );
  });

  it('marks each month with its coverage', () => {
    renderGrid();
    const coverage = (label: string) => screen.getByText(`${label}:`).parentElement;
    expect(coverage('january')).toHaveTextContent(/in$/);
    expect(coverage('february')).toHaveTextContent(/not sent yet$/);
    expect(coverage('spring biannual')).toHaveTextContent(/0 free$/);
  });

  it('toggles a month from its header', async () => {
    const { onToggleSlot } = renderGrid();
    await userEvent.click(screen.getByRole('button', { name: 'january' }));
    expect(onToggleSlot).toHaveBeenCalledWith('s1');
  });

  it('marks the open month as pressed', () => {
    renderGrid({ openSlotId: 's1' });
    const pressed = (name: string) =>
      screen.getByRole('button', { name }).getAttribute('aria-pressed');
    expect(pressed('january')).toBe('true');
    expect(pressed('february')).toBe('false');
  });

  it('proposes a free planner from their tile', async () => {
    const { act } = renderGrid();
    await userEvent.click(screen.getByRole('button', { name: 'propose ada for january' }));
    expect(act).toHaveBeenCalledWith(grid.slots[1], grid.planners[0], 'available', undefined);
  });

  it('locks every tile while busy', () => {
    renderGrid({ busy: true });
    const tiles = screen.getAllByRole('button', { name: /^(propose|remove draft|withdraw) / });
    expect(tiles).toHaveLength(9);
    for (const tile of tiles) expect(tile).toBeDisabled();
  });

  it('lists submitted planners first with their load, then the rest with – twice', () => {
    renderGrid();
    const cells = screen.getAllByText(/^(ada|bo|cy|–|\d+\/\d+)$/).map((el) => el.textContent);
    expect(cells).toEqual(['ada', '0/2', 'bo', '2/1', 'cy', '–', '–']);
  });

  it('labels the monthlies and biannual columns as their form, short on phones', () => {
    renderGrid();
    expect(screen.getByText('form')).toHaveClass('md:hidden');
    expect(screen.getByText('their form')).toHaveClass('hidden', 'md:inline');
    for (const word of ['mo', 'bi']) expect(screen.getByText(word)).toHaveClass('md:hidden');
    for (const word of ['monthlies', 'biannual']) {
      expect(screen.getByText(word)).toHaveClass('hidden', 'md:inline');
    }
  });

  it("shows each planner's biannual interest", () => {
    renderGrid();
    expect(screen.getByText('biannual: yes')).toBeInTheDocument();
    expect(screen.getByText('biannual: maybe')).toBeInTheDocument();
    expect(screen.getByText('biannual: no answer')).toBeInTheDocument();
  });

  it('spells out the extra slot markers in the key', () => {
    renderGrid();
    expect(screen.getByText('★ spring biannual')).toBeInTheDocument();
  });
});
