import { useEffect, useRef, useState } from 'react';

import type { PlannerColumn, PlanningGrid } from '@/api/planning';
import { Button } from '@/components/ui/Button';

import {
  type CellState,
  cellState,
  findAssignment,
  isWithdrawable,
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
  readOnly?: boolean;
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

interface RowAction {
  text: string;
  disabled?: boolean;
  run: () => void;
}

interface PanelRow {
  planner: PlannerColumn;
  detail?: string;
  notes?: string[];
  actions: RowAction[];
}

function Section({ title, rows, busy }: { title: string; rows: PanelRow[]; busy: boolean }) {
  if (rows.length === 0) return null;
  return (
    <>
      <h3 className="mt-3 text-xs font-semibold">{title}</h3>
      <ul className="mt-1 space-y-2">
        {rows.map((row) => (
          <li key={row.planner.userId} className="flex items-center gap-2">
            <span className="min-w-0 flex-1">
              <span className="flex flex-wrap items-baseline gap-x-2">
                <span className="truncate">{row.planner.name}</span>
                {row.notes?.map((note) => (
                  <span key={note} className="text-muted text-xs">
                    {note}
                  </span>
                ))}
              </span>
              {row.detail && <span className="text-muted block text-xs">{row.detail}</span>}
            </span>
            {row.actions.map((action) => (
              <Button
                key={action.text}
                variant="secondary"
                className="h-8 px-3"
                aria-label={`${action.text} ${row.planner.name}`}
                disabled={busy || action.disabled}
                onClick={action.run}
              >
                {action.text}
              </Button>
            ))}
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

function plannerNotes(planner: PlannerColumn, extraSlot: boolean): string[] {
  const notes: string[] = [];
  if (extraSlot && planner.biannualInterest) notes.push(`biannual: ${planner.biannualInterest}`);
  if (!planner.hasEmail) notes.push('no email');
  if (!planner.isPlanner) notes.push('no longer a planner');
  return notes;
}

type Act = MonthPanelProps['act'];

function panelRows(grid: PlanningGrid, slot: PlanningGrid['slots'][number], act?: Act) {
  const planning: PanelRow[] = [];
  const asked: PanelRow[] = [];
  const free: PanelRow[] = [];
  const noForm: PanelRow[] = [];
  for (const planner of grid.planners) {
    const state = cellState(slot.id, planner.userId, grid);
    const assignment = findAssignment(grid, slot.id, planner.userId);
    const notes = plannerNotes(planner, slot.kind !== 'monthly');
    const action = (text: string, disabled: boolean): RowAction[] =>
      act ? [{ text, disabled, run: () => void act(slot, planner, state, assignment) }] : [];
    if (assignment) {
      const disabled = !isWithdrawable(state) && !planner.isPlanner;
      const row = { planner, notes, actions: action(actionText(state), disabled) };
      if (state === 'committed') planning.push(row);
      else asked.push({ ...row, detail: STATE_TEXT[state] });
    } else if (state === 'available') {
      const detail = loadText(grid, planner);
      free.push({ planner, notes, detail, actions: action('propose', !planner.isPlanner) });
    } else if (planner.isPlanner && !planner.submitted) {
      noForm.push({ planner, notes, actions: action('propose', false) });
    }
  }
  return { planning, asked, free, noForm };
}

function addText(adding: boolean, freeCount: number): string {
  if (adding) return 'hide';
  return freeCount > 0 ? `add someone · ${String(freeCount)} free` : 'add someone';
}

export function MonthPanel({
  grid,
  slotId,
  today,
  act,
  busy,
  readOnly = false,
  onClose,
}: MonthPanelProps) {
  const [adding, setAdding] = useState(false);
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    ref.current?.scrollIntoView({ block: 'nearest' });
  }, [slotId]);
  const slot = grid.slots.find((s) => s.id === slotId);
  if (!slot) return null;
  const { planning, asked, free, noForm } = panelRows(grid, slot, readOnly ? undefined : act);

  return (
    <section
      ref={ref}
      aria-labelledby="month-panel-heading"
      className="border-border rounded-md border p-3 text-sm"
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <h2 id="month-panel-heading" className="font-semibold">
            {slot.label}
          </h2>
          <p className="text-muted text-xs">{TAG[slotCoverage(grid, slotId, today).kind]}</p>
          <SlotEventLink
            slot={slot}
            year={grid.year}
            canCreate={!readOnly && slotHasCommitted(grid, slotId)}
          />
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
      <Section title="planning" rows={planning} busy={busy} />
      <Section title="asked" rows={asked} busy={busy} />
      {adding && (
        <>
          <Section title="free" rows={free} busy={busy} />
          <Section title="no form" rows={noForm} busy={busy} />
        </>
      )}
      {!readOnly && free.length + noForm.length > 0 && (
        <Button
          variant="secondary"
          className="mt-3 h-8 px-3"
          aria-expanded={adding}
          onClick={() => {
            setAdding(!adding);
          }}
        >
          {addText(adding, free.length)}
        </Button>
      )}
    </section>
  );
}
