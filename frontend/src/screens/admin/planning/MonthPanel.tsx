import { useEffect, useRef } from 'react';

import type { Assignment, PlannerColumn, PlanningGrid } from '@/api/planning';
import { Button } from '@/components/ui/Button';

import {
  type CellState,
  cellState,
  findAssignment,
  slotHasCommitted,
  STATE_TEXT,
} from './gridCell';
import { type Coverage, plannerLoad, slotCoverage } from './gridSummary';
import { SlotEventLink } from './SlotEventLink';
import type { usePlanningActions } from './usePlanningActions';

interface MonthPanelProps {
  grid: PlanningGrid;
  slotId: string;
  today: Date;
  act: ReturnType<typeof usePlanningActions>['act'];
  busy: boolean;
  onClose: () => void;
}

const TAG: Record<Coverage['kind'], string> = {
  in: 'covered',
  sent: 'waiting',
  draft: 'not sent yet',
  free: 'needs a planner',
  past: 'past',
};

function actionText(state: CellState): string {
  if (state === 'draft') return 'undo';
  if (state === 'declined') return 'propose again';
  return 'withdraw';
}

interface PanelRow {
  planner: PlannerColumn;
  state: CellState;
  assignment?: Assignment;
  detail: string;
  text: string;
  disabled?: boolean;
}

function Section({
  title,
  rows,
  busy,
  onAct,
}: {
  title: string;
  rows: PanelRow[];
  busy: boolean;
  onAct: (row: PanelRow) => void;
}) {
  if (rows.length === 0) return null;
  return (
    <>
      <h3 className="mt-3 text-xs font-semibold">{title}</h3>
      <ul className="mt-1 space-y-2">
        {rows.map((row) => (
          <li key={row.planner.userId} className="flex items-center gap-2">
            <span className="min-w-0 flex-1">
              <span className="block truncate">{row.planner.name}</span>
              <span className="text-muted block text-xs">{row.detail}</span>
            </span>
            <Button
              variant="secondary"
              className="h-8 px-3"
              disabled={busy || row.disabled}
              onClick={() => {
                onAct(row);
              }}
            >
              {row.text}
            </Button>
          </li>
        ))}
      </ul>
    </>
  );
}

function loadText(grid: PlanningGrid, planner: PlannerColumn): string {
  const load = plannerLoad(grid, planner);
  return load ? `${String(load.taken)} of ${String(load.offered)} monthlies taken` : '';
}

export function MonthPanel({ grid, slotId, today, act, busy, onClose }: MonthPanelProps) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    ref.current?.scrollIntoView({ block: 'nearest' });
  }, [slotId]);
  const slot = grid.slots.find((s) => s.id === slotId);
  if (!slot) return null;
  const onIt: PanelRow[] = [];
  const free: PanelRow[] = [];
  for (const planner of grid.planners) {
    const state = cellState(slotId, planner.userId, grid, today);
    const assignment = findAssignment(grid, slotId, planner.userId);
    if (assignment) {
      onIt.push({ planner, state, assignment, detail: STATE_TEXT[state], text: actionText(state) });
    } else if (state === 'available') {
      const detail = loadText(grid, planner);
      free.push({ planner, state, detail, text: 'propose', disabled: !planner.isPlanner });
    }
  }
  const onAct = (row: PanelRow) => void act(slot, row.planner, row.state, row.assignment);

  return (
    <section
      ref={ref}
      aria-labelledby="month-panel-heading"
      className="border-border rounded-md border p-3 text-sm md:w-72 md:shrink-0"
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <h2 id="month-panel-heading" className="font-semibold">
            {slot.label}
          </h2>
          <p className="text-muted text-xs">{TAG[slotCoverage(grid, slotId, today).kind]}</p>
          <SlotEventLink slot={slot} year={grid.year} canCreate={slotHasCommitted(grid, slotId)} />
        </div>
        <Button
          variant="ghost"
          className="h-10 min-w-10 px-2"
          aria-label={`close ${slot.label}`}
          onClick={onClose}
        >
          ×
        </Button>
      </div>
      <Section title="on it" rows={onIt} busy={busy} onAct={onAct} />
      <Section title="free" rows={free} busy={busy} onAct={onAct} />
    </section>
  );
}
