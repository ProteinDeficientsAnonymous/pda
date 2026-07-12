import { useState } from 'react';

import type { PublicRsvpOut } from '@/api/publicRsvp';
import type { Event } from '@/models/event';

import { PublicRsvpConfirmation } from './PublicRsvpConfirmation';
import { PublicRsvpForm } from './PublicRsvpForm';

interface Props {
  event: Event;
}

export function PublicRsvpSection({ event }: Props) {
  const [result, setResult] = useState<PublicRsvpOut | null>(null);
  if (result) return <PublicRsvpConfirmation event={event} result={result} />;
  return <PublicRsvpForm event={event} onSuccess={setResult} />;
}
