import type { Assignment, PlannerColumn, PlanningSlot } from '@/api/planning';

import { type CellState, isWithdrawable } from './gridCell';

const CELL_TEXT: Record<CellState, string> = {
  committed: 'committed',
  proposed: 'proposed',
  no_answer: 'no answer',
  declined: 'declined',
  available: 'available',
  blank: '',
};

interface GridCellProps {
  slot: PlanningSlot;
  planner: PlannerColumn;
  state: CellState;
  assignment: Assignment | undefined;
  disabled: boolean;
  onAct: (state: CellState, assignment: Assignment | undefined) => void;
}

export function GridCell({ slot, planner, state, assignment, disabled, onAct }: GridCellProps) {
  const textId = `cell-${slot.id}-${planner.userId}`;
  const withdrawable = isWithdrawable(state);
  const blockedReason = !withdrawable && !planner.isPlanner ? 'no longer a planner' : null;
  const label = withdrawable
    ? `withdraw ${planner.name} from ${slot.label}`
    : `propose ${planner.name} for ${slot.label}`;
  return (
    <td className="px-1 py-1">
      <button
        type="button"
        aria-label={label}
        aria-describedby={textId}
        title={blockedReason ?? undefined}
        disabled={disabled || blockedReason !== null}
        onClick={() => {
          onAct(state, assignment);
        }}
        className="hover:bg-surface-dim min-h-9 w-full rounded px-2 py-1 text-left disabled:opacity-50"
      >
        <span id={textId}>
          {CELL_TEXT[state] || <span className="sr-only">not available</span>}
          {blockedReason ? <span className="sr-only"> · {blockedReason}</span> : null}
        </span>
      </button>
    </td>
  );
}
