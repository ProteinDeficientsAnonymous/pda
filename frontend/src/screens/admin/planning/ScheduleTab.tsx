import { useState } from 'react';

import { usePlanningGrid } from '@/api/planning';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { summaryCounts } from './gridSummary';
import { MonthPanel } from './MonthPanel';
import { ScheduleGrid } from './ScheduleGrid';
import { SendProposalsBar } from './SendProposalsBar';
import { SummaryPills } from './SummaryPills';
import { usePlanningActions } from './usePlanningActions';

export function ScheduleTab({ year }: { year: number }) {
  const { data: grid, isPending, isError } = usePlanningGrid(year);
  const [today] = useState(() => new Date());
  const [openSlotId, setOpenSlotId] = useState<string | null>(null);
  const { act, tap, busy, send, confirmElement } = usePlanningActions(year);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the planning grid — try refreshing" />;
  if (grid.planners.length === 0) return <p className="text-muted text-sm">no planners yet 🌿</p>;

  return (
    <>
      <SummaryPills counts={summaryCounts(grid, today)} />
      <div className="flex flex-col gap-4">
        <div className="min-w-0 flex-1">
          <ScheduleGrid
            grid={grid}
            today={today}
            openSlotId={openSlotId}
            onToggleSlot={(slotId) => {
              setOpenSlotId((open) => (open === slotId ? null : slotId));
            }}
            act={tap}
            busy={busy}
          />
        </div>
        {openSlotId ? (
          <MonthPanel
            key={openSlotId}
            grid={grid}
            slotId={openSlotId}
            today={today}
            act={act}
            busy={busy}
            onClose={() => {
              setOpenSlotId(null);
              document.getElementById(`month-${openSlotId}`)?.focus();
            }}
          />
        ) : null}
        <SendProposalsBar grid={grid} send={send} act={act} busy={busy} />
      </div>
      {confirmElement}
    </>
  );
}
