import { useState } from 'react';

import {
  type PlanningGrid as Grid,
  type PlannerColumn,
  type PlanningSlot,
  usePlanningGrid,
} from '@/api/planning';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { cellState, findAssignment, slotHasCommitted, slotNeedsPlanner } from './gridCell';
import { GridCell } from './PlanningGridCell';
import { SlotEventLink } from './SlotEventLink';
import { usePlanningActions } from './usePlanningActions';

function PlannerHeader({ planner }: { planner: PlannerColumn }) {
  return (
    <th scope="col" className="min-w-28 px-3 py-2 text-left align-bottom font-medium">
      <div>{planner.name}</div>
      {planner.submitted ? (
        <div className="text-muted text-xs font-normal">
          biannual: {planner.biannualInterest ?? 'none'} · monthly: {planner.monthlyCount}
        </div>
      ) : (
        <div className="text-muted text-xs font-normal">not submitted</div>
      )}
      {planner.hasEmail ? null : <div className="text-xs font-normal">no email</div>}
    </th>
  );
}

function SlotHeader({ slot, year, grid }: { slot: PlanningSlot; year: number; grid: Grid }) {
  return (
    <th scope="row" className="bg-surface sticky left-0 px-3 py-2 text-left font-medium">
      <div>{slot.label}</div>
      {slotNeedsPlanner(grid, slot.id) ? (
        <div className="text-xs font-normal">needs a planner</div>
      ) : null}
      <div className="font-normal">
        <SlotEventLink slot={slot} year={year} canCreate={slotHasCommitted(grid, slot.id)} />
      </div>
    </th>
  );
}

export function PlanningGrid({ year }: { year: number }) {
  const { data: grid, isPending, isError } = usePlanningGrid(year);
  const [today] = useState(() => new Date());
  const { act, busy, confirmElement } = usePlanningActions(year);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the planning grid — try refreshing" />;
  if (grid.planners.length === 0) return <p className="text-muted text-sm">no planners yet 🌿</p>;

  return (
    <section className="mt-8">
      <h2 className="mb-3 text-lg font-medium">planning grid</h2>
      {/* relative: the cells' sr-only labels are absolute and would otherwise widen the page on phones */}
      <div className="border-border relative overflow-x-auto rounded-lg border">
        <table aria-label="planning grid" className="w-full border-collapse text-sm">
          <thead>
            <tr>
              <th scope="col" className="px-3 py-2 text-left font-medium">
                slot
              </th>
              {grid.planners.map((p) => (
                <PlannerHeader key={p.userId} planner={p} />
              ))}
            </tr>
          </thead>
          <tbody>
            {grid.slots.map((slot) => (
              <tr key={slot.id} className="border-border border-t">
                <SlotHeader slot={slot} year={year} grid={grid} />
                {grid.planners.map((p) => (
                  <GridCell
                    key={p.userId}
                    slot={slot}
                    planner={p}
                    state={cellState(slot.id, p.userId, grid, today)}
                    assignment={findAssignment(grid, slot.id, p.userId)}
                    disabled={busy}
                    onAct={(state, assignment) => void act(slot, p, state, assignment)}
                  />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {confirmElement}
    </section>
  );
}
