import type { PlanningGrid } from '@/api/planning';
import { Button } from '@/components/ui/Button';

import { slotHasCommitted } from './gridCell';
import { type Coverage, slotCoverage } from './gridSummary';
import { SlotEventLink } from './SlotEventLink';

interface MonthPanelProps {
  grid: PlanningGrid;
  slotId: string;
  year: number;
  today: Date;
  onClose: () => void;
}

const TAG: Record<Coverage['kind'], string> = {
  in: 'covered',
  sent: 'waiting',
  draft: 'waiting',
  free: 'needs a planner',
  past: 'past',
};

export function MonthPanel({ grid, slotId, year, today, onClose }: MonthPanelProps) {
  const slot = grid.slots.find((s) => s.id === slotId);
  if (!slot) return null;

  return (
    <section
      aria-labelledby="month-panel-heading"
      className="border-border rounded-md border p-3 text-sm md:w-72 md:shrink-0"
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <h2 id="month-panel-heading" className="font-semibold">
            {slot.label}
          </h2>
          <p className="text-muted text-xs">{TAG[slotCoverage(grid, slotId, today).kind]}</p>
          <SlotEventLink slot={slot} year={year} canCreate={slotHasCommitted(grid, slotId)} />
        </div>
        <Button
          variant="ghost"
          className="h-8 px-2"
          aria-label={`close ${slot.label}`}
          onClick={onClose}
        >
          ×
        </Button>
      </div>
    </section>
  );
}
