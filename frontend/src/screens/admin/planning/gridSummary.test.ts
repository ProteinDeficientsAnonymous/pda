import { describe, expect, it } from 'vitest';

import type { Assignment, PlannerColumn, PlanningGrid } from '@/api/planning';
import { makeAssignment, makePlanner, makePlanningGrid, makeSlot } from '@/test/fixtures';

import { needsPlanner, plannerLoad, slotCoverage, summaryCounts } from './gridSummary';

const today = new Date(2027, 1, 15);

const planner = (userId: string, overrides: Partial<PlannerColumn> = {}) =>
  makePlanner({ userId, name: userId, biannualInterest: 'yes', monthlyCount: 2, ...overrides });

const asg = (slotId: string, userId: string, status: Assignment['status']) =>
  makeAssignment({ id: `${slotId}-${userId}`, slotId, userId, status });

const makeGrid = (planners: PlannerColumn[], assignments: Assignment[] = [], month = 3) =>
  makePlanningGrid({ year: 2027, slots: [makeSlot({ id: 's1', month })], planners, assignments });

describe('slotCoverage', () => {
  it('prefers committed over proposed over draft', () => {
    const ps = [planner('u1'), planner('u2'), planner('u3')];
    const all = [
      asg('s1', 'u1', 'draft'),
      asg('s1', 'u2', 'proposed'),
      asg('s1', 'u3', 'committed'),
    ];
    expect(slotCoverage(makeGrid(ps, all), 's1', today)).toEqual({ kind: 'in' });
    expect(slotCoverage(makeGrid(ps, all.slice(0, 2)), 's1', today)).toEqual({ kind: 'sent' });
    expect(slotCoverage(makeGrid(ps, all.slice(0, 1)), 's1', today)).toEqual({ kind: 'draft' });
  });

  it('ignores withdrawn assignments', () => {
    const grid = makeGrid([planner('u1')], [asg('s1', 'u1', 'withdrawn')]);
    expect(slotCoverage(grid, 's1', today)).toEqual({ kind: 'free', count: 0 });
  });

  it('counts free planners who marked the slot, excluding declined ones', () => {
    const ps = [
      planner('u1', { availableSlotIds: ['s1'] }),
      planner('u2', { availableSlotIds: ['s1'] }),
      planner('u3', { availableSlotIds: ['s1'] }),
      planner('u4'),
    ];
    const grid = makeGrid(ps, [asg('s1', 'u2', 'declined')]);
    expect(slotCoverage(grid, 's1', today)).toEqual({ kind: 'free', count: 2 });
  });

  it('does not count ex-planners who marked the slot as free', () => {
    const ps = [
      planner('u1', { availableSlotIds: ['s1'] }),
      planner('u2', { isPlanner: false, availableSlotIds: ['s1'] }),
    ];
    expect(slotCoverage(makeGrid(ps), 's1', today)).toEqual({ kind: 'free', count: 1 });
  });

  it('is past for an ended slot with nothing, sent for one with a proposal', () => {
    expect(slotCoverage(makeGrid([planner('u1')], [], 1), 's1', today)).toEqual({ kind: 'past' });
    const proposed = makeGrid([planner('u1')], [asg('s1', 'u1', 'proposed')], 1);
    expect(slotCoverage(proposed, 's1', today)).toEqual({ kind: 'sent' });
  });
});

describe('needsPlanner', () => {
  it('is true for an empty future or current-month slot, false for past or covered', () => {
    expect(needsPlanner(makeGrid([planner('u1')]), 's1', today)).toBe(true);
    expect(needsPlanner(makeGrid([planner('u1')], [], 2), 's1', today)).toBe(true);
    expect(needsPlanner(makeGrid([planner('u1')], [], 1), 's1', today)).toBe(false);
    const proposed = makeGrid([planner('u1')], [asg('s1', 'u1', 'proposed')], 1);
    expect(needsPlanner(proposed, 's1', today)).toBe(false);
  });
});

describe('plannerLoad', () => {
  it('counts draft, proposed and committed monthly slots but not biannual', () => {
    const grid: PlanningGrid = {
      year: 2027,
      slots: [
        makeSlot({ id: 'm1', month: 3 }),
        makeSlot({ id: 'm2', month: 4 }),
        makeSlot({ id: 'm3', month: 5 }),
        makeSlot({ id: 'm4', month: 7 }),
        makeSlot({ id: 'b1', month: 6, kind: 'biannual' }),
      ],
      planners: [planner('u1', { monthlyCount: 3 })],
      assignments: [
        asg('m1', 'u1', 'draft'),
        asg('m2', 'u1', 'committed'),
        asg('m3', 'u1', 'declined'),
        asg('m4', 'u1', 'proposed'),
        asg('b1', 'u1', 'committed'),
      ],
    };
    expect(plannerLoad(grid, grid.planners[0]!)).toEqual({ taken: 3, offered: 3 });
  });

  it('is null when the planner has not submitted', () => {
    const p = planner('u1', { submitted: false });
    expect(plannerLoad(makeGrid([p]), p)).toBeNull();
  });
});

describe('summaryCounts', () => {
  it('counts slots needing a planner, waiting proposals and missing forms', () => {
    const grid: PlanningGrid = {
      year: 2027,
      slots: [
        makeSlot({ id: 'past', month: 1 }),
        makeSlot({ id: 'a', month: 3 }),
        makeSlot({ id: 'b', month: 4 }),
        makeSlot({ id: 'c', month: 5 }),
      ],
      planners: [
        planner('u1', { availableSlotIds: ['a', 'b'] }),
        planner('u2', { submitted: false }),
        planner('u3', { isPlanner: false, submitted: false }),
      ],
      assignments: [asg('c', 'u1', 'proposed')],
    };
    expect(summaryCounts(grid, today)).toEqual({ needPlanner: 2, waiting: 1, noForm: 1 });
  });
});
