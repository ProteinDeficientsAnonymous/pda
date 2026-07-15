import { useNavigate } from 'react-router-dom';

import type { Event } from '@/models/event';

import { PublicRsvpForm } from './PublicRsvpForm';

interface Props {
  event: Event;
}

export function PublicRsvpSection({ event }: Props) {
  const navigate = useNavigate();
  return (
    <PublicRsvpForm
      event={event}
      onSuccess={(result) => {
        navigate(`/events/${event.id}?rsvp_token=${encodeURIComponent(result.rsvp_token)}`, {
          replace: true,
        });
      }}
    />
  );
}
