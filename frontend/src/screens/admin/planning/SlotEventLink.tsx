import { Link } from 'react-router-dom';

import type { PlanningSlot } from '@/api/planning';
import { useHasPermission } from '@/auth/useAuth';
import { eventPath } from '@/models/event';
import { Permission } from '@/models/permissions';

interface Props {
  slot: PlanningSlot;
  year: number;
  canCreate: boolean;
}

export function SlotEventLink({ slot, year, canCreate }: Props) {
  const canTagOfficial = useHasPermission(Permission.TagOfficialEvent);
  if (slot.eventId) {
    return (
      <Link
        className="text-xs underline"
        to={eventPath({ id: slot.eventId, slug: slot.eventSlug ?? '' })}
      >
        view event
      </Link>
    );
  }
  if (!canCreate || !canTagOfficial) return null;
  return (
    <Link
      className="text-xs underline"
      to={`/events/add?planningSlot=${slot.id}&year=${String(year)}`}
    >
      create event
    </Link>
  );
}
