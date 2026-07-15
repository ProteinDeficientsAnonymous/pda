import type { Event } from '@/models/event';

import { EventCommentsCard } from './comments/EventCommentsCard';
import { CostSection, LinksSection, LocationSection } from './EventMemberSection';
import { RsvpGuestList } from './RsvpGuestList';

interface Props {
  event: Event;
  token: string;
}

export function EventPublicRsvpSection({ event, token }: Props) {
  const rsvpDisabled = !event.rsvpEnabled;
  return (
    <div className="mt-8 flex flex-col gap-6">
      <LocationSection event={event} />
      <LinksSection event={event} />
      <CostSection event={event} />
      {event.isPast || rsvpDisabled ? null : (
        <section className="border-border bg-surface rounded-lg border p-4">
          <h2 className="text-muted mb-3 text-xs font-medium tracking-wide">rsvp</h2>
          <RsvpGuestList event={event} canSeeInvited={false} />
        </section>
      )}
      {rsvpDisabled ? null : <EventCommentsCard eventId={event.id} token={token} />}
    </div>
  );
}
