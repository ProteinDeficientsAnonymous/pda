import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { type Event, RsvpServerStatus } from '@/models/event';
import { formatEventDateTime } from '@/utils/datetime';

function formatDeadline(deadline: Date): string {
  return formatEventDateTime(deadline, null);
}

function closedDetail(myRsvp: string | null): string {
  if (myRsvp === RsvpServerStatus.Attending || myRsvp === RsvpServerStatus.Waitlisted) {
    return "you can still switch to can't go";
  }
  if (myRsvp === null) return "new rsvps aren't being taken";
  return "rsvps can't be changed anymore";
}

export function RsvpDeadlineNote({ event, closed }: { event: Event; closed: boolean }) {
  if (!event.rsvpDeadline) return null;
  const when = formatDeadline(event.rsvpDeadline);
  if (!closed) {
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
