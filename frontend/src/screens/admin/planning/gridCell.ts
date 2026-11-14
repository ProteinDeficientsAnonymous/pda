import type { Assignment, PlanningGrid } from '@/api/planning';

export type CellState = 'committed' | 'proposed' | 'no_answer' | 'declined' | 'available' | 'blank';

export function findAssignment(
  grid: PlanningGrid,
  slotId: string,
  userId: string,
): Assignment | undefined {
  return grid.assignments.find((a) => a.slotId === slotId && a.userId === userId);
}

export function cellState(
  slotId: string,
  userId: string,
  grid: PlanningGrid,
  today: Date,
): CellState {
  const status = findAssignment(grid, slotId, userId)?.status;
  if (status === 'committed') return 'committed';
  if (status === 'proposed') {
    const slot = grid.slots.find((s) => s.id === slotId);
    const started = slot !== undefined && today >= new Date(grid.year, slot.month - 1, 1);
    return started ? 'no_answer' : 'proposed';
  }
  if (status === 'declined') return 'declined';
  const planner = grid.planners.find((p) => p.userId === userId);
  return planner?.availableSlotIds.includes(slotId) ? 'available' : 'blank';
}

const WITHDRAWABLE: CellState[] = ['committed', 'proposed', 'no_answer'];

export function isWithdrawable(state: CellState): boolean {
  return WITHDRAWABLE.includes(state);
}
