import type { EventFormValues } from '@/api/eventWrites';
import { EventVisibility, isOfficialOrClub } from '@/models/event';

export function typeDefaults(type: EventFormValues['eventType']): Partial<EventFormValues> {
  return isOfficialOrClub(type) ? { visibility: EventVisibility.Public, allowPlusOnes: false } : {};
}
