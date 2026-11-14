import { describe, expect, it } from 'vitest';

import type { Assignment, PlanningGrid } from '@/api/planning';

import { cellState, findAssignment } from './gridCell';

const slot = (id: string, month: number) => ({
  id,
  label: id,
  month,
  kind: 'monthly' as const,
  order: month,
  eventId: null,
  eventSlug: null,
  eventStatus: null,
});

function makeGrid(
  assignments: Pick<Assignment, 'status'>[] = [],
  availableSlotIds: string[] = [],
): PlanningGrid {
  return {
    year: 2027,
    slots: [slot('s1', 3)],
    planners: [
      {
        userId: 'u1',
        name: 'ada',
        isPlanner: true,
        hasEmail: true,
        submitted: true,
        biannualInterest: 'yes',
        monthlyCount: 1,
        availableSlotIds,
      },
    ],
    assignments: assignments.map((a, i) => ({
      id: `a${String(i)}`,
      slotId: 's1',
      userId: 'u1',
      status: a.status,
    })),
  };
}

const early = new Date(2027, 0, 15);

describe('cellState', () => {
  it('is blank with no availability and no assignment', () => {
    expect(cellState('s1', 'u1', makeGrid(), early)).toBe('blank');
  });

  it('is available when the planner offered the slot', () => {
    expect(cellState('s1', 'u1', makeGrid([], ['s1']), early)).toBe('available');
  });

  it('ranks declined above available', () => {
    expect(cellState('s1', 'u1', makeGrid([{ status: 'declined' }], ['s1']), early)).toBe(
      'declined',
    );
  });

  it('ranks proposed above declined and available', () => {
    expect(cellState('s1', 'u1', makeGrid([{ status: 'proposed' }], ['s1']), early)).toBe(
      'proposed',
    );
  });

  it('ranks committed above everything', () => {
    const grid = makeGrid([{ status: 'committed' }], ['s1']);
    expect(cellState('s1', 'u1', grid, early)).toBe('committed');
  });

  it('turns proposed into no_answer once the slot month has started', () => {
    const grid = makeGrid([{ status: 'proposed' }]);
    expect(cellState('s1', 'u1', grid, new Date(2027, 1, 28))).toBe('proposed');
    expect(cellState('s1', 'u1', grid, new Date(2027, 2, 1))).toBe('no_answer');
  });

  it('keeps committed after the slot month has started', () => {
    const grid = makeGrid([{ status: 'committed' }]);
    expect(cellState('s1', 'u1', grid, new Date(2027, 5, 1))).toBe('committed');
  });

  it('finds the assignment for a slot and user', () => {
    const grid = makeGrid([{ status: 'proposed' }]);
    expect(findAssignment(grid, 's1', 'u1')?.id).toBe('a0');
    expect(findAssignment(grid, 's1', 'u2')).toBeUndefined();
  });
});
