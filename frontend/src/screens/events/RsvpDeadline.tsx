import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { type Event, isRsvpDeadlinePassed, RsvpServerStatus } from '@/models/event';
import { formatEventDateTime } from '@/utils/datetime';

import { RSVP_PILL_CLASSES } from './rsvpPill';

function formatDeadline(deadline: Date): string {
  return formatEventDateTime(deadline, null);
}

function closedDetail(myRsvp: string | null): string {
  if (myRsvp === RsvpServerStatus.Waitlisted) return 'you can still leave the waitlist';
  if (myRsvp === RsvpServerStatus.Attending) return "you can still switch to can't go";
  if (myRsvp === null) return "new rsvps aren't being taken";
  return "rsvps can't be changed anymore";
}

export function RsvpsClosedButton() {
  return (
    <button
      type="button"
      disabled
      className={`${RSVP_PILL_CLASSES} disabled:bg-toggle-off disabled:cursor-not-allowed`}
    >
      rsvps are closed
    </button>
  );
}

export function RsvpDeadlineNote({ event, closed }: { event: Event; closed: boolean }) {
  if (closed && event.rsvpsClosed) {
    // with no rsvp, the closed button already says it all
    if (event.myRsvp === null) return null;
    return (
      <p role="status" className="text-foreground-secondary text-center text-sm">
        rsvps are closed — {closedDetail(event.myRsvp)}
      </p>
    );
  }
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

export function MaybeDeadlineDialog({
  deadline,
  onClose,
}: {
  deadline: Date;
  onClose: () => void;
}) {
  const when = formatDeadline(deadline);
  return (
    <Dialog open title={`confirm by ${when}`} onClose={onClose}>
      <p className="text-foreground-secondary mb-4 text-sm">
        you're a maybe — switch to going or can't go by {when}. after that, rsvps close and a maybe
        can't be changed. we'll email you a reminder the day before.
      </p>
      <div className="flex justify-end">
        <Button onClick={onClose}>got it</Button>
      </div>
    </Dialog>
  );
}
