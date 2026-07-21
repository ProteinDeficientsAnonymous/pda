import { useNavigate } from 'react-router-dom';

import { setStoredRsvpToken } from '@/api/rsvpTokenStorage';
import type { Event } from '@/models/event';

import { PublicRsvpForm } from './PublicRsvpForm';

interface Props {
  event: Event;
}

export function PublicRsvpSection({ event }: Props) {
  const navigate = useNavigate();

  function unlockWithToken(token: string) {
    // kept out of the url — this page's url is shared, and a token there would leak rsvp identity
    setStoredRsvpToken(token);
    void navigate(0);
  }

  return (
    <PublicRsvpForm
      event={event}
      onSuccess={(result) => {
        unlockWithToken(result.rsvp_token);
      }}
    />
  );
}
