import { Fragment } from 'react';

import type { PlannerColumn, PlanningGrid } from '@/api/planning';
import { cn } from '@/utils/cn';

import { cellState, findAssignment } from './gridCell';
import { gridTemplate, loadTrack, slotColumns } from './gridLayout';
import { CoverageMark, GridKey } from './GridMarks';
import { LoadCell, NameCell } from './GridRowCells';
import { plannerLoad, slotCoverage } from './gridSummary';
import { GridTile } from './GridTile';
import type { usePlanningActions } from './usePlanningActions';

interface ScheduleGridProps {
  grid: PlanningGrid;
  today: Date;
  openSlotId: string | null;
  onToggleSlot: (slotId: string) => void;
  act: ReturnType<typeof usePlanningActions>['act'];
  busy: boolean;
}

const at = (row: number, column: number | string) => ({ gridRow: row, gridColumn: column });

const ROW = '22px';

function rowTemplate(submitted: number, notSubmitted: number): string {
  const rows = [ROW, ROW, '1px', ...Array<string>(submitted).fill(ROW)];
  if (submitted > 0 && notSubmitted > 0) rows.push('1px');
  return [...rows, ...Array<string>(notSubmitted).fill(ROW)].join(' ');
}

function Divider({ row }: { row: number }) {
  return <div aria-hidden="true" style={at(row, '1 / -1')} className="bg-border" />;
}

export function ScheduleGrid({
  grid,
  today,
  openSlotId,
  onToggleSlot,
  act,
  busy,
}: ScheduleGridProps) {
  const columns = slotColumns(grid.slots);
  const loadColumn = loadTrack(columns);
  const submitted = grid.planners.filter((p) => p.submitted);
  const notSubmitted = grid.planners.filter((p) => !p.submitted);
  const split = submitted.length > 0 && notSubmitted.length > 0;
  const laterStart = 4 + submitted.length + (split ? 1 : 0);

  const plannerRow = (planner: PlannerColumn, row: number) => (
    <Fragment key={planner.userId}>
      <NameCell planner={planner} style={at(row, 1)} />
      {columns.map(({ slot, track }) => {
        const state = cellState(slot.id, planner.userId, grid, today);
        const assignment = findAssignment(grid, slot.id, planner.userId);
        return (
          <div key={slot.id} style={at(row, track)}>
            <GridTile
              state={state}
              plannerName={planner.name}
              slotLabel={slot.label}
              isPlanner={planner.isPlanner}
              disabled={busy}
              onAct={() => void act(slot, planner, state, assignment)}
            />
          </div>
        );
      })}
      <LoadCell load={plannerLoad(grid, planner)} style={at(row, loadColumn)} />
    </Fragment>
  );

  return (
    <div>
      <div className="relative overflow-x-auto py-0.5">
        <div
          className="mx-auto grid w-max"
          style={{
            gridTemplateColumns: gridTemplate(columns),
            gridTemplateRows: rowTemplate(submitted.length, notSubmitted.length),
          }}
        >
          <span style={at(2, 1)} className="text-muted self-center text-xs">
            month
          </span>
          {columns.map(({ slot, header, track }) => {
            const open = slot.id === openSlotId;
            return (
              <Fragment key={slot.id}>
                <button
                  type="button"
                  style={at(1, track)}
                  aria-label={slot.label}
                  aria-pressed={open}
                  onClick={() => {
                    onToggleSlot(slot.id);
                  }}
                  className={cn(
                    'focus-visible:outline-plan-ink rounded text-[11px] font-semibold focus-visible:outline-2',
                    open ? 'bg-plan-ink text-plan-ink-fg' : 'hover:bg-plan-blank',
                  )}
                >
                  {header}
                </button>
                <div
                  style={at(2, track)}
                  className="flex items-center justify-center text-[10px] font-semibold"
                >
                  <span className="sr-only">{`${slot.label}: `}</span>
                  <CoverageMark coverage={slotCoverage(grid, slot.id, today)} />
                </div>
              </Fragment>
            );
          })}
          <Divider row={3} />
          {submitted.map((p, i) => plannerRow(p, 4 + i))}
          {split ? <Divider row={laterStart - 1} /> : null}
          {notSubmitted.map((p, i) => plannerRow(p, laterStart + i))}
        </div>
      </div>
      <GridKey columns={columns} />
    </div>
  );
}
