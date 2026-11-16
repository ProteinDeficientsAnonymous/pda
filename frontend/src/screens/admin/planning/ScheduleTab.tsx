import { useState } from 'react';

import { usePlanningGrid } from '@/api/planning';

import { PlanningGrid } from './PlanningGrid';
import { ScheduleGrid } from './ScheduleGrid';
import { usePlanningActions } from './usePlanningActions';

export function ScheduleTab({ year }: { year: number }) {
  const { data: grid } = usePlanningGrid(year);
  const [today] = useState(() => new Date());
  const [openSlotId, setOpenSlotId] = useState<string | null>(null);
  const { act, busy, confirmElement } = usePlanningActions(year);

  return (
    <>
      {grid && grid.planners.length > 0 ? (
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
      ) : null}
      {confirmElement}
      <PlanningGrid year={year} />
    </>
  );
}
