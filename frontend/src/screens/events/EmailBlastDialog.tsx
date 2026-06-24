// Email-blast compose dialog for event hosts/co-hosts.
//
// Two steps: compose (subject + message + audience + recipient preview) then a
// confirm step (blasts are irreversible). On success, a toast shows how many
// were emailed and how many were skipped for having no email on file.

import { useState } from 'react';
import { toast } from 'sonner';
import { useEmailBlast } from '@/api/eventBlast';
import { extractApiErrorOr } from '@/api/apiErrors';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { RsvpServerStatus, type Event } from '@/models/event';

interface Props {
  event: Event;
  open: boolean;
  onClose: () => void;
}

const SUBJECT_MAX = 150;
const MESSAGE_MAX = 5000;

// Audience presets map to backend RSVPStatus lists. `everyone` omits the
// audience so the backend defaults to all RSVP statuses (including can't-go).
const AUDIENCE_EVERYONE = 'everyone';
const AUDIENCE_GOING = 'going';
const AUDIENCE_GOING_MAYBE = 'going_maybe';

const AUDIENCE_OPTIONS = [
  { value: AUDIENCE_EVERYONE, label: "everyone who rsvp'd (incl. can't go)" },
  { value: AUDIENCE_GOING, label: 'going + waitlist' },
  { value: AUDIENCE_GOING_MAYBE, label: 'going + waitlist + maybe' },
];

function statusesForAudience(audience: string): string[] | null {
  if (audience === AUDIENCE_GOING) {
    return [RsvpServerStatus.Attending, RsvpServerStatus.Waitlisted];
  }
  if (audience === AUDIENCE_GOING_MAYBE) {
    return [RsvpServerStatus.Attending, RsvpServerStatus.Waitlisted, RsvpServerStatus.Maybe];
  }
  // everyone → let the backend apply its default (all statuses)
  return null;
}

function recipientCount(event: Event, audience: string): number {
  const statuses = statusesForAudience(audience);
  if (statuses === null) return event.guests.length;
  const allowed = new Set(statuses);
  return event.guests.filter((g) => allowed.has(g.status)).length;
}

export function EmailBlastDialog({ event, open, onClose }: Props) {
  const blast = useEmailBlast(event.id);
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [audience, setAudience] = useState(AUDIENCE_EVERYONE);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const count = recipientCount(event, audience);

  function reset() {
    setSubject('');
    setMessage('');
    setAudience(AUDIENCE_EVERYONE);
    setConfirming(false);
    setError(null);
  }

  function handleClose() {
    if (blast.isPending) return;
    reset();
    onClose();
  }

  function goToConfirm() {
    setError(null);
    if (!subject.trim()) {
      setError('add a subject');
      return;
    }
    if (!message.trim()) {
      setError('add a message');
      return;
    }
    setConfirming(true);
  }

  async function send() {
    setError(null);
    const statuses = statusesForAudience(audience);
    try {
      const result = await blast.mutateAsync({
        subject: subject.trim(),
        message: message.trim(),
        ...(statuses ? { audience: statuses } : {}),
      });
      const skipped =
        result.skipped_no_email_count > 0
          ? `, ${String(result.skipped_no_email_count)} skipped (no email)`
          : '';
      const noun = result.sent_count === 1 ? 'attendee' : 'attendees';
      toast.success(`sent to ${String(result.sent_count)} ${noun}${skipped} 🌱`);
      reset();
      onClose();
    } catch (err) {
      setError(extractApiErrorOr(err, "couldn't send — try again"));
    }
  }

  if (confirming) {
    return (
      <Dialog open={open} onClose={handleClose} title="send email blast?">
        <p className="text-foreground-secondary text-sm">
          email <strong>{count}</strong> {count === 1 ? 'attendee' : 'attendees'}? this can't be
          undone — anyone without an email on file will be skipped.
        </p>
        {error ? (
          <p role="alert" className="mt-3 text-sm text-red-600">
            {error}
          </p>
        ) : null}
        <div className="mt-4 flex justify-end gap-2">
          <Button
            variant="ghost"
            onClick={() => {
              setConfirming(false);
            }}
            disabled={blast.isPending}
          >
            back
          </Button>
          <Button
            onClick={() => {
              void send();
            }}
            disabled={blast.isPending}
          >
            {blast.isPending ? 'sending…' : 'send'}
          </Button>
        </div>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onClose={handleClose} title="email attendees">
      <div className="flex flex-col gap-3">
        <TextField
          label="subject"
          value={subject}
          maxLength={SUBJECT_MAX}
          onChange={(e) => {
            setSubject(e.target.value);
          }}
        />
        <div className="flex flex-col gap-1">
          <label htmlFor="blast-message" className="text-foreground text-sm font-medium">
            message
          </label>
          <textarea
            id="blast-message"
            value={message}
            maxLength={MESSAGE_MAX}
            onChange={(e) => {
              setMessage(e.target.value);
            }}
            className="border-border-strong bg-surface focus:ring-brand-200 focus:border-brand-500 h-32 w-full rounded-md border px-3 py-2 text-sm transition-colors outline-none focus:ring-2"
          />
        </div>
        <Select
          label="send to"
          options={AUDIENCE_OPTIONS}
          value={audience}
          onChange={(e) => {
            setAudience(e.target.value);
          }}
        />
        <p className="text-muted text-xs">
          emailing {count} {count === 1 ? 'attendee' : 'attendees'} — anyone without an email is
          skipped
        </p>
      </div>
      {error ? (
        <p role="alert" className="mt-3 text-sm text-red-600">
          {error}
        </p>
      ) : null}
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="ghost" onClick={handleClose}>
          cancel
        </Button>
        <Button onClick={goToConfirm} disabled={count === 0}>
          next
        </Button>
      </div>
    </Dialog>
  );
}
