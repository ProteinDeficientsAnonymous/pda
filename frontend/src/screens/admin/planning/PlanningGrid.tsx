import { useState } from 'react';
import { Link } from 'react-router-dom';

import { type PlannerColumn, type PlanningSlot, usePlanningGrid } from '@/api/planning';
import { eventPath } from '@/models/event';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { type CellState, cellState } from './gridCell';

const CELL_TEXT: Record<CellState, string> = {
  committed: 'committed',
  proposed: 'proposed',
  no_answer: 'no answer',
  declined: 'declined',
  available: 'available',
  blank: '',
};

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

function SlotHeader({ slot }: { slot: PlanningSlot }) {
  return (
    <th scope="row" className="bg-surface sticky left-0 px-3 py-2 text-left font-medium">
      <div>{slot.label}</div>
      {slot.eventId ? (
        <div className="text-xs font-normal">
          scheduled ·{' '}
          <Link
            className="underline"
            to={eventPath({ id: slot.eventId, slug: slot.eventSlug ?? '' })}
          >
            view event
          </Link>
        </div>
      ) : null}
    </th>
  );
}

export function PlanningGrid({ year }: { year: number }) {
  const { data: grid, isPending, isError } = usePlanningGrid(year);
  const [today] = useState(() => new Date());

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the planning grid — try refreshing" />;
  if (grid.planners.length === 0) return <p className="text-muted text-sm">no planners yet 🌿</p>;

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
                <SlotHeader slot={slot} />
                {grid.planners.map((p) => {
                  const state = cellState(slot.id, p.userId, grid, today);
                  return (
                    <td key={p.userId} className="px-3 py-2">
                      {CELL_TEXT[state] || <span className="sr-only">not available</span>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
