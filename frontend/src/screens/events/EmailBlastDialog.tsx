import { useMemo, useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useEmailBlast } from '@/api/eventBlast';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { TextField } from '@/components/ui/TextField';
import { type Event, RsvpServerStatus } from '@/models/event';

interface Props {
  event: Event;
  open: boolean;
  onClose: () => void;
}

const SUBJECT_MAX = 150;
const MESSAGE_MAX = 5000;

const AUDIENCE_LABELS: { value: string; label: string }[] = [
  { value: RsvpServerStatus.Attending, label: 'going' },
  { value: RsvpServerStatus.Maybe, label: 'maybe' },
  { value: RsvpServerStatus.CantGo, label: "can't go" },
  { value: RsvpServerStatus.Waitlisted, label: 'waitlisted' },
];

interface AudienceGroup {
  value: string;
  label: string;
  count: number;
}

function availableAudiences(event: Event): AudienceGroup[] {
  return AUDIENCE_LABELS.map(({ value, label }) => ({
    value,
    label,
    count: event.guests.filter((g) => g.status === value).length,
  })).filter((o) => o.count > 0);
}

function countForSelected(event: Event, selected: Set<string>): number {
  return event.guests.filter((g) => selected.has(g.status)).length;
}

export function EmailBlastDialog({ event, open, onClose }: Props) {
  const blast = useEmailBlast(event.id);
  const audiences = useMemo(() => availableAudiences(event), [event]);
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(availableAudiences(event).map((a) => a.value)),
  );
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const count = countForSelected(event, selected);

  function toggle(value: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  }

  function reset() {
    setSubject('');
    setMessage('');
    setSelected(new Set(audiences.map((a) => a.value)));
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
    const statuses = [...selected];
    try {
      const result = await blast.mutateAsync({
        subject: subject.trim(),
        message: message.trim(),
        audience: statuses,
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
    <Dialog open={open} onClose={handleClose} title="email blast">
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
            className="border-border-strong bg-surface focus:ring-brand-200 focus:border-brand-500 h-32 w-full rounded-md border px-3 py-2 text-base transition-colors outline-none focus:ring-2 md:text-sm"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <span className="text-foreground text-sm font-medium">send to</span>
          <div className="flex flex-wrap gap-1.5">
            {audiences.map((a) => (
              <AudienceChip
                key={a.value}
                label={a.label}
                count={a.count}
                active={selected.has(a.value)}
                onToggle={() => {
                  toggle(a.value);
                }}
              />
            ))}
          </div>
        </div>
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

function AudienceChip({
  label,
  count,
  active,
  onToggle,
}: {
  label: string;
  count: number;
  active: boolean;
  onToggle: () => void;
}) {
  const base =
    'inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs transition-colors';
  const activeCls = 'border-brand-300 bg-brand-100 text-brand-700';
  const idleCls =
    'border-border text-foreground-secondary hover:border-border-strong hover:text-foreground';
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={active}
      className={`${base} ${active ? activeCls : idleCls}`}
    >
      {label}
      <span className="opacity-60">{String(count)}</span>
    </button>
  );
}
