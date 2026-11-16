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

export function SlotEventLink({ slot, year, canCreate, asButton = false }: Props) {
  if (slot.eventId) {
    return (
      <span className="text-xs">
        {slot.eventStatus ? `${STATUS_TEXT[slot.eventStatus]} · ` : null}
        <Link
          className="underline"
          to={eventPath({ id: slot.eventId, slug: slot.eventSlug ?? '' })}
        >
          view event
        </Link>
      </span>
    );
  }
  if (!canCreate) return null;
  return (
    <Link
      className={asButton ? buttonClass('secondary') : 'text-xs underline'}
      to={`/events/add?planningSlot=${slot.id}&year=${String(year)}`}
    >
      create event
    </Link>
  );
}
