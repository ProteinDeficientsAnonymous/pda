// Host-only "group text" action (creator/co-host) — see issue #500. Mobile opens
// the host's Messages app as a group thread; desktop copies the list instead.

import { toast } from 'sonner';
import type { Event } from '@/models/event';
import { buildSmsUri, collectRecipients, isSmsSupported } from '@/utils/groupText';

interface Props {
  event: Event;
}

function skippedNote(count: number): string {
  const subject = count === 1 ? 'attendee has' : 'attendees have';
  return `${String(count)} ${subject} no number and weren't included`;
}

export function GroupTextButton({ event }: Props) {
  // Audience is everyone who RSVP'd; the backend only sends `phone` to hosts.
  const { phones, skippedCount } = collectRecipients(event.guests);
  const smsSupported = isSmsSupported();

  function handleClick() {
    if (phones.length === 0) {
      toast.error('no attendee phone numbers to text');
      return;
    }

    if (smsSupported) {
      const uri = buildSmsUri(phones);
      if (uri) window.location.href = uri;
      // Messages won't show who was dropped, so flag skipped attendees here.
      if (skippedCount > 0) toast.info(skippedNote(skippedCount));
      return;
    }

    void navigator.clipboard
      .writeText(phones.join(', '))
      .then(() => {
        const note = skippedCount > 0 ? ` — ${skippedNote(skippedCount)}` : '';
        toast.success(`copied ${String(phones.length)} numbers${note}`);
      })
      .catch(() => {
        toast.error("couldn't copy — try again");
      });
  }

  const label = smsSupported ? 'text attendees' : 'copy attendee numbers';
  const disabled = phones.length === 0;

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled}
      aria-label={label}
      title={disabled ? 'no attendee phone numbers to text' : label}
      className="bg-surface-dim text-foreground-secondary hover:bg-surface-dim/70 hover:text-foreground inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50"
    >
      <MessageIcon />
      {label}
    </button>
  );
}

function MessageIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  );
}
