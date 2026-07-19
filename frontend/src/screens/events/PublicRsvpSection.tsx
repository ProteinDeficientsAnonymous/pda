import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { setStoredRsvpToken } from '@/api/rsvpTokenStorage';
import type { Event } from '@/models/event';

import { PublicRsvpForm } from './PublicRsvpForm';

interface Props {
  event: Event;
}

export function PublicRsvpSection({ event }: Props) {
  const navigate = useNavigate();
  const [isMember, setIsMember] = useState(false);

  function unlockWithToken(token: string) {
    // kept out of the url — this page's url is shared, and a token there would leak rsvp identity
    setStoredRsvpToken(token);
    void navigate(0);
  }

  if (isMember) return <MemberSignInPrompt />;

  return (
    <PublicRsvpForm
      event={event}
      onSuccess={(result) => {
        unlockWithToken(result.rsvp_token);
      }}
      onMember={() => {
        setIsMember(true);
      }}
      onAlreadyRsvpd={(result) => {
        unlockWithToken(result.rsvpToken);
      }}
    />
  );
}

function MemberSignInPrompt() {
  return (
    <section aria-label="rsvp" className="border-border bg-surface mt-8 rounded-lg border p-6">
      <h2 className="mb-2 text-base font-medium">looks like you already have an account</h2>
      <p className="text-foreground-tertiary mb-4 text-sm">sign in to rsvp to this event</p>
      <Link
        to="/login"
        className="bg-brand-600 text-brand-on hover:bg-brand-700 inline-flex h-10 items-center rounded-md px-4 text-sm font-medium"
      >
        sign in
      </Link>
    </section>
  );
}
