import { useNavigate } from 'react-router-dom';

import { setStoredRsvpToken } from '@/api/rsvpTokenStorage';
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
        // Persist so the token survives navigation — a returning non-member
        // reuses it across events instead of re-filling the form (issue #873).
        setStoredRsvpToken(result.rsvp_token);
        void navigate(`/events/${event.id}?rsvp_token=${encodeURIComponent(result.rsvp_token)}`, {
          replace: true,
        });
      }}
    />
  );
}
