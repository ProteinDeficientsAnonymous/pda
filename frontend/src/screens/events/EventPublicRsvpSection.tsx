import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { clearStoredRsvpToken } from '@/api/rsvpTokenStorage';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import type { Event } from '@/models/event';

import { EventCommentsCard } from './comments/EventCommentsCard';
import { CostSection, LinksSection, LocationSection } from './EventMemberSection';
import { RsvpSection } from './RsvpSection';

interface Props {
  event: Event;
  token: string;
}

export function EventPublicRsvpSection({ event, token }: Props) {
  const navigate = useNavigate();
  const rsvpDisabled = !event.rsvpEnabled;
  const [forgetOpen, setForgetOpen] = useState(false);

  function handleForget() {
    clearStoredRsvpToken();
    setForgetOpen(false);
    void navigate('/calendar');
  }

  return (
    <div className="mt-8 flex flex-col gap-6">
      <LocationSection event={event} />
      <LinksSection event={event} />
      <CostSection event={event} />
      {event.isPast || rsvpDisabled ? null : (
        <section className="border-border bg-surface rounded-lg border p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-muted text-xs font-medium tracking-wide">rsvp</h2>
            <button
              type="button"
              onClick={() => {
                setForgetOpen(true);
              }}
              className="text-foreground-secondary text-xs underline underline-offset-2"
            >
              not you?
            </button>
          </div>
          <RsvpSection event={event} canSeeInvited={false} token={token} />
        </section>
      )}
      {rsvpDisabled ? null : <EventCommentsCard eventId={event.id} token={token} />}

      <ConfirmDialog
        open={forgetOpen}
        title="not you?"
        message="this'll forget your rsvps on this device — you can always rsvp again to get a new link"
        confirmLabel="forget me"
        cancelLabel="cancel"
        destructive={false}
        onCancel={() => {
          setForgetOpen(false);
        }}
        onConfirm={handleForget}
      />
    </div>
  );
}
