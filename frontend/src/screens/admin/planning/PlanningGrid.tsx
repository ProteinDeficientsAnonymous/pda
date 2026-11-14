import { useState } from 'react';

import {
  type Assignment,
  type PlannerColumn,
  type PlanningSlot,
  usePlanningGrid,
  usePropose,
  useWithdraw,
} from '@/api/planning';
import { useConfirm } from '@/components/ui/useConfirm';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { type CellState, cellState, findAssignment, isWithdrawable } from './gridCell';
import { GridCell } from './PlanningGridCell';
import { SlotEventLink } from './SlotEventLink';
import { toastOnError } from './toastOnError';

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

function SlotHeader({ slot, year }: { slot: PlanningSlot; year: number }) {
  return (
    <th scope="row" className="bg-surface sticky left-0 px-3 py-2 text-left font-medium">
      <div>{slot.label}</div>
      <div className="text-xs font-normal">
        {slot.eventId ? 'scheduled · ' : null}
        <SlotEventLink slot={slot} year={year} canCreate />
      </div>
    </th>
  );
}

export function PlanningGrid({ year }: { year: number }) {
  const { data: grid, isPending, isError } = usePlanningGrid(year);
  const [today] = useState(() => new Date());
  const propose = usePropose(year);
  const withdraw = useWithdraw(year);
  const { confirm, element } = useConfirm();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the planning grid — try refreshing" />;
  if (grid.planners.length === 0) return <p className="text-muted text-sm">no planners yet 🌿</p>;

  async function act(
    slot: PlanningSlot,
    planner: PlannerColumn,
    state: CellState,
    assignment: Assignment | undefined,
  ) {
    if (!isWithdrawable(state)) {
      await toastOnError(
        propose.mutateAsync({ slotId: slot.id, userId: planner.userId }),
        "couldn't propose that slot — try again",
      );
      return;
    }
    const ok = await confirm({
      message: `withdraw ${planner.name} from ${slot.label}?`,
      confirmLabel: 'withdraw',
      destructive: true,
    });
    if (ok && assignment) {
      await toastOnError(
        withdraw.mutateAsync(assignment.id),
        "couldn't withdraw that slot — try again",
      );
    }
  }

  return (
    <section className="mt-8">
      <h2 className="mb-3 text-lg font-medium">planning grid</h2>
      <div className="border-border overflow-x-auto rounded-lg border">
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
                <SlotHeader slot={slot} year={year} />
                {grid.planners.map((p) => (
                  <GridCell
                    key={p.userId}
                    slot={slot}
                    planner={p}
                    state={cellState(slot.id, p.userId, grid, today)}
                    assignment={findAssignment(grid, slot.id, p.userId)}
                    disabled={propose.isPending || withdraw.isPending}
                    onAct={(state, assignment) => void act(slot, p, state, assignment)}
                  />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {element}
    </section>
  );
}
