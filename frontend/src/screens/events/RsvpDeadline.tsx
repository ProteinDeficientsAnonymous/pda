import { type Event, isRsvpDeadlinePassed, RsvpServerStatus } from '@/models/event';
import { formatEventDateTime } from '@/utils/datetime';

function formatDeadline(deadline: Date): string {
  return formatEventDateTime(deadline, null);
}

function closedDetail(myRsvp: string | null): string {
  if (myRsvp === RsvpServerStatus.Waitlisted) return 'you can still leave the waitlist';
  if (myRsvp === RsvpServerStatus.Attending) return "you can still switch to can't go";
  if (myRsvp === null) return "new rsvps aren't being taken";
  return "rsvps can't be changed anymore";
}

export function RsvpDeadlineNote({ event, closed }: { event: Event; closed: boolean }) {
  if (!event.rsvpDeadline) return null;
  const when = formatDeadline(event.rsvpDeadline);
  if (!closed) {
    // hosts are exempt from the deadline, so it's no longer worth showing them
    if (isRsvpDeadlinePassed(event)) return null;
    return <p className="text-foreground-secondary text-center text-xs">rsvp by {when}</p>;
  }
  return (
    <p role="status" className="text-foreground-secondary text-center text-sm">
      the rsvp deadline was {when} — {closedDetail(event.myRsvp)}
    </p>
  );
}
