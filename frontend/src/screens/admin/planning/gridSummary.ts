import type { Assignment, PlannerColumn, PlanningGrid } from '@/api/planning';

export type Coverage =
  | { kind: 'in' }
  | { kind: 'sent' }
  | { kind: 'draft' }
  | { kind: 'free'; count: number }
  | { kind: 'past' };

const LOADING: Assignment['status'][] = ['draft', 'proposed', 'committed'];

export function slotEnded(year: number, month: number, today: Date): boolean {
  return today >= new Date(year, month, 1);
}

export function slotCoverage(grid: PlanningGrid, slotId: string, today: Date): Coverage {
  const onSlot = grid.assignments.filter((a) => a.slotId === slotId);
  const has = (status: Assignment['status']) => onSlot.some((a) => a.status === status);
  if (has('committed')) return { kind: 'in' };
  if (has('proposed')) return { kind: 'sent' };
  if (has('draft')) return { kind: 'draft' };
  const slot = grid.slots.find((s) => s.id === slotId);
  if (slot && slotEnded(grid.year, slot.month, today)) return { kind: 'past' };
  const declined = new Set(onSlot.filter((a) => a.status === 'declined').map((a) => a.userId));
  const count = grid.planners.filter(
    (p) => p.isPlanner && p.availableSlotIds.includes(slotId) && !declined.has(p.userId),
  ).length;
  return { kind: 'free', count };
}

export function needsPlanner(grid: PlanningGrid, slotId: string, today: Date): boolean {
  return slotCoverage(grid, slotId, today).kind === 'free';
}

export function plannerLoad(
  grid: PlanningGrid,
  planner: PlannerColumn,
): { taken: number; offered: number } | null {
  if (!planner.submitted) return null;
  const monthly = new Set(grid.slots.filter((s) => s.kind === 'monthly').map((s) => s.id));
  const taken = grid.assignments.filter(
    (a) => a.userId === planner.userId && monthly.has(a.slotId) && LOADING.includes(a.status),
  ).length;
  return { taken, offered: planner.monthlyCount };
}

export function summaryCounts(
  grid: PlanningGrid,
  today: Date,
): { needPlanner: number; waiting: number; noForm: number } {
  return {
    needPlanner: grid.slots.filter((s) => needsPlanner(grid, s.id, today)).length,
    waiting: grid.assignments.filter((a) => a.status === 'proposed').length,
    noForm: grid.planners.filter((p) => p.isPlanner && !p.submitted).length,
  };
}
