import { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

import { extractApiErrorOr, getApiStatus } from '@/api/apiErrors';
import { useCancelPublicMyRsvp, useUpdatePublicMyRsvp } from '@/api/publicRsvp';
import { Button } from '@/components/ui/Button';
import { RsvpStatusPicker } from '@/components/ui/RsvpStatusPicker';
import { type Event, type RsvpInputStatus, RsvpServerStatus } from '@/models/event';
import { formatEventDateTime } from '@/utils/datetime';
import { buildEventLinks } from '@/utils/eventLinks';

import { RsvpCommentField } from './RsvpCommentField';

const UPDATED_TOAST = 'rsvp updated — check your email for an updated link';

const STATUS_LABELS: Record<string, string> = {
  [RsvpServerStatus.Attending]: "you're going",
  [RsvpServerStatus.Maybe]: "you're a maybe",
  [RsvpServerStatus.CantGo]: "you can't go",
  [RsvpServerStatus.Waitlisted]: "you're on the waitlist",
};

function errorMessage(err: unknown): string {
  const status = getApiStatus(err);
  if (status === 429) return "you're going too fast — try again in a few minutes";
  if (status === 404) return "this rsvp isn't available anymore — refresh";
  // 400s carry an actionable backend message (event full, invalid status).
  return extractApiErrorOr(err, 'something went wrong — try again');
}

interface Props {
  token: string;
  event: Event;
  status: string;
}

export function PublicRsvpCard({ token, event, status }: Props) {
  const update = useUpdatePublicMyRsvp(token);
  const cancel = useCancelPublicMyRsvp(token);
  const [error, setError] = useState<string | null>(null);
  const [comment, setComment] = useState('');
  const links = buildEventLinks(event);
  const busy = update.isPending || cancel.isPending;

  async function applyRsvp(next: RsvpInputStatus, rsvpComment?: string) {
    setError(null);
    try {
      await update.mutateAsync({
        eventId: event.id,
        status: next,
        hasPlusOne: false,
        ...(rsvpComment !== undefined ? { comment: rsvpComment } : {}),
      });
      toast.success(UPDATED_TOAST);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  function changeStatus(next: RsvpInputStatus) {
    if (next === status) return;
    void applyRsvp(next);
  }

  function saveComment() {
    const trimmed = comment.trim();
    if (!trimmed) return;
    void applyRsvp(status as RsvpInputStatus, trimmed);
    setComment('');
  }

  async function cancelRsvp() {
    setError(null);
    try {
      await cancel.mutateAsync(event.id);
      toast.success('rsvp cancelled');
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section aria-label={event.title} className="border-border bg-surface rounded-lg border p-6">
      <Link
        to={`/events/${event.id}`}
        className="text-foreground text-lg font-medium hover:underline"
      >
        <h2>{event.title}</h2>
      </Link>
      {event.startDatetime ? (
        <p className="text-foreground-secondary text-sm">
          {formatEventDateTime(event.startDatetime, event.endDatetime, event.datetimeTbd)}
        </p>
      ) : null}
      {event.location ? (
        <p className="text-foreground-secondary text-sm">{event.location}</p>
      ) : null}
      {links.length > 0 ? (
        <ul className="mt-2 flex flex-col gap-1">
          {links.map((l) => (
            <li key={l.url}>
              <a
                href={l.url}
                target="_blank"
                rel="noreferrer"
                className="text-info text-sm hover:underline"
              >
                {l.label}
              </a>
            </li>
          ))}
        </ul>
      ) : null}

      <p role="status" className="text-foreground-tertiary mt-4 mb-2 text-sm">
        {STATUS_LABELS[status] ?? 'your rsvp'}
      </p>
      <div className="flex flex-col gap-3">
        <RsvpStatusPicker value={status} onSelect={changeStatus} disabled={busy} />

        <RsvpCommentField value={comment} onChange={setComment} disabled={busy} />
        <Button variant="ghost" onClick={saveComment} disabled={busy || !comment.trim()}>
          save comment
        </Button>

        <Button variant="ghost" onClick={() => void cancelRsvp()} disabled={busy}>
          cancel rsvp
        </Button>

        {error ? (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        ) : null}
      </div>
    </section>
  );
}
