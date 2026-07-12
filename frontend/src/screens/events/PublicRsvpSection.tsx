import { useState } from 'react';

import type { PublicRsvpOut } from '@/api/publicRsvp';
import { type Event, EventStatus, EventType, EventVisibility } from '@/models/event';

import { PublicRsvpConfirmation } from './PublicRsvpConfirmation';
import { PublicRsvpForm } from './PublicRsvpForm';

export function canPublicRsvp(event: Event): boolean {
  return (
    event.eventType === EventType.Official &&
    event.visibility === EventVisibility.Public &&
    event.rsvpEnabled &&
    event.status !== EventStatus.Cancelled &&
    !event.isPast
  );
}

interface Props {
  event: Event;
}

export function PublicRsvpSection({ event }: Props) {
  const [result, setResult] = useState<PublicRsvpOut | null>(null);
  if (result) return <PublicRsvpConfirmation event={event} result={result} />;
  return <PublicRsvpForm event={event} onSuccess={setResult} />;
}
