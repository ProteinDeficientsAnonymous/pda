import { Link } from 'react-router-dom';

import type { PlanningSlot } from '@/api/planning';
import { buttonClass } from '@/components/ui/buttonClass';
import { eventPath } from '@/models/event';

interface Props {
  slot: PlanningSlot;
  year: number;
  canCreate: boolean;
  asButton?: boolean;
}

const STATUS_TEXT: Record<NonNullable<PlanningSlot['eventStatus']>, string> = {
  active: 'scheduled',
  draft: 'draft',
  cancelled: 'cancelled',
  deleted: 'deleted',
};

export function SlotEventStatus({ slot }: { slot: PlanningSlot }) {
  if (!slot.eventId || !slot.eventStatus) return null;
  return (
    <span className="bg-surface-dim text-foreground-secondary rounded-full px-2 py-0.5 text-xs font-normal">
      {STATUS_TEXT[slot.eventStatus]}
    </span>
  );
}

export function SlotEventLink({ slot, year, canCreate, asButton = false }: Props) {
  if (slot.eventId) {
    const to = eventPath({ id: slot.eventId, slug: slot.eventSlug ?? '' });
    if (asButton) {
      return (
        <Link className={buttonClass()} to={to}>
          view event
        </Link>
      );
    }
    return (
      <span className="text-xs">
        {slot.eventStatus ? `${STATUS_TEXT[slot.eventStatus]} · ` : null}
        <Link className="underline" to={to}>
          view event
        </Link>
      </span>
    );
  }
  if (!canCreate) return null;
  return (
    <Link
      className={asButton ? buttonClass() : 'text-xs underline'}
      to={`/events/add?planningSlot=${slot.id}&year=${String(year)}`}
    >
      create event
    </Link>
  );
}
