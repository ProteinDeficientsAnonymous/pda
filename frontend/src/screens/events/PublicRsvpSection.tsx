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
    // Persist so the token survives navigation — a returning non-member
    // reuses it across events instead of re-filling the form (issue #873).
    // Kept out of the URL (issue #918) — this page's URL is what people
    // copy/paste to share the event, and a token there would leak whoever
    // clicks it into the sharer's RSVP identity.
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
