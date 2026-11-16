import { describe, expect, it } from 'vitest';

import type { Assignment, PlanningGrid } from '@/api/planning';
import { makeAssignment, makePlanner, makePlanningGrid, makeSlot } from '@/test/fixtures';

import {
  cellActionLabel,
  type CellState,
  cellState,
  findAssignment,
  isWithdrawable,
  slotHasCommitted,
} from './gridCell';

const slot = (id: string, month: number) => makeSlot({ id, label: id, month, order: month });

function makeGrid(
  assignments: Pick<Assignment, 'status'>[] = [],
  availableSlotIds: string[] = [],
): PlanningGrid {
  return makePlanningGrid({
    year: 2027,
    slots: [slot('s1', 3)],
    planners: [makePlanner({ biannualInterest: 'yes', availableSlotIds })],
    assignments: assignments.map((a, i) =>
      makeAssignment({ id: `a${String(i)}`, status: a.status }),
    ),
  });
}

describe('cellState', () => {
  it('is blank with no availability and no assignment', () => {
    expect(cellState('s1', 'u1', makeGrid())).toBe('blank');
  });

  it('is available when the planner offered the slot', () => {
    expect(cellState('s1', 'u1', makeGrid([], ['s1']))).toBe('available');
  });

  it('ranks declined above available', () => {
    expect(cellState('s1', 'u1', makeGrid([{ status: 'declined' }], ['s1']))).toBe('declined');
  });

  it('shows a draft row as draft', () => {
    expect(cellState('s1', 'u1', makeGrid([{ status: 'draft' }], ['s1']))).toBe('draft');
  });

  it('ranks proposed above declined and available', () => {
    expect(cellState('s1', 'u1', makeGrid([{ status: 'proposed' }], ['s1']))).toBe('proposed');
  });

  it('ranks committed above everything', () => {
    const grid = makeGrid([{ status: 'committed' }], ['s1']);
    expect(cellState('s1', 'u1', grid)).toBe('committed');
  });

  it('finds the assignment for a slot and user', () => {
    const grid = makeGrid([{ status: 'proposed' }]);
    expect(findAssignment(grid, 's1', 'u1')?.id).toBe('a0');
    expect(findAssignment(grid, 's1', 'u2')).toBeUndefined();
  });
});

describe('isWithdrawable', () => {
  it.each<[CellState, boolean]>([
    ['committed', true],
    ['proposed', true],
    ['draft', true],
    ['declined', false],
    ['available', false],
    ['blank', false],
  ])('%s -> %s', (state, expected) => {
    expect(isWithdrawable(state)).toBe(expected);
  });
});

describe('cellActionLabel', () => {
  it.each<[CellState, string]>([
    ['draft', 'remove draft ada for january'],
    ['committed', 'withdraw ada from january'],
    ['available', 'propose ada for january'],
  ])('%s -> %s', (state, expected) => {
    expect(cellActionLabel(state, 'ada', 'january')).toBe(expected);
  });
});

describe('slotHasCommitted', () => {
  it.each<[Assignment['status'], boolean]>([
    ['committed', true],
    ['proposed', false],
    ['draft', false],
  ])('%s -> %s', (status, expected) => {
    expect(slotHasCommitted(makeGrid([{ status }]), 's1')).toBe(expected);
  });
});
