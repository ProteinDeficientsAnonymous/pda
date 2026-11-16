import { useEffect, useRef } from 'react';

import type { PlanningGrid } from '@/api/planning';
import { Button } from '@/components/ui/Button';

import { slotHasCommitted } from './gridCell';
import { type Coverage, slotCoverage } from './gridSummary';
import { SlotEventLink } from './SlotEventLink';

interface MonthPanelProps {
  grid: PlanningGrid;
  slotId: string;
  today: Date;
  onClose: () => void;
}

const TAG: Record<Coverage['kind'], string> = {
  in: 'covered',
  sent: 'waiting',
  draft: 'not sent yet',
  free: 'needs a planner',
  past: 'past',
};

export function MonthPanel({ grid, slotId, today, onClose }: MonthPanelProps) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    ref.current?.scrollIntoView({ block: 'nearest' });
  }, [slotId]);
  const slot = grid.slots.find((s) => s.id === slotId);
  if (!slot) return null;

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
    </section>
  );
}
