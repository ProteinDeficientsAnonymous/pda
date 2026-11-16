import type { Assignment, PlanningGrid } from '@/api/planning';

export type CellState = 'committed' | 'proposed' | 'draft' | 'declined' | 'available' | 'blank';

export function findAssignment(
  grid: PlanningGrid,
  slotId: string,
  userId: string,
): Assignment | undefined {
  return grid.assignments.find((a) => a.slotId === slotId && a.userId === userId);
}

export function cellState(slotId: string, userId: string, grid: PlanningGrid): CellState {
  const status = findAssignment(grid, slotId, userId)?.status;
  if (status === 'committed') return 'committed';
  if (status === 'proposed') return 'proposed';
  if (status === 'draft') return 'draft';
  if (status === 'declined') return 'declined';
  const planner = grid.planners.find((p) => p.userId === userId);
  return planner?.availableSlotIds.includes(slotId) ? 'available' : 'blank';
}

function slotStatuses(grid: PlanningGrid, slotId: string): Assignment['status'][] {
  return grid.assignments.filter((a) => a.slotId === slotId).map((a) => a.status);
}

export function slotHasCommitted(grid: PlanningGrid, slotId: string): boolean {
  return slotStatuses(grid, slotId).includes('committed');
}

export function draftCount(grid: PlanningGrid): number {
  return grid.assignments.filter((a) => a.status === 'draft').length;
}

const WITHDRAWABLE: CellState[] = ['committed', 'proposed', 'draft'];

export function isWithdrawable(state: CellState): boolean {
  return WITHDRAWABLE.includes(state);
}

export const STATE_TEXT: Record<CellState, string> = {
  committed: 'in',
  proposed: 'sent',
  draft: 'not sent yet',
  declined: 'declined',
  available: 'free',
  blank: 'not free',
};

export function cellActionLabel(state: CellState, plannerName: string, slotLabel: string): string {
  if (state === 'draft') return `remove draft ${plannerName} for ${slotLabel}`;
  if (isWithdrawable(state)) return `withdraw ${plannerName} from ${slotLabel}`;
  return `propose ${plannerName} for ${slotLabel}`;
}
