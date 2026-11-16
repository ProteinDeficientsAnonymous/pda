import { useState } from 'react';

import { usePlanningGrid } from '@/api/planning';

import { draftCount } from './gridCell';
import { summaryCounts } from './gridSummary';
import { PlanningGrid } from './PlanningGrid';
import { ScheduleGrid } from './ScheduleGrid';
import { SendProposalsBar } from './SendProposalsBar';
import { SummaryPills } from './SummaryPills';
import { usePlanningActions } from './usePlanningActions';

export function ScheduleTab({ year }: { year: number }) {
  const { data: grid } = usePlanningGrid(year);
  const [today] = useState(() => new Date());
  const [openSlotId, setOpenSlotId] = useState<string | null>(null);
  const { act, busy, send, confirmElement } = usePlanningActions(year);

  return (
    <>
      {grid ? <SendProposalsBar send={send} drafts={draftCount(grid)} /> : null}
      {grid && grid.planners.length > 0 ? (
        <>
          <SummaryPills counts={summaryCounts(grid, today)} />
          <ScheduleGrid
            grid={grid}
            today={today}
            openSlotId={openSlotId}
            onToggleSlot={(slotId) => {
              setOpenSlotId((open) => (open === slotId ? null : slotId));
            }}
            act={act}
            busy={busy}
          />
        </>
      ) : null}
      {confirmElement}
      <PlanningGrid year={year} />
    </>
  );
}
