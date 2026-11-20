import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useUpdateEvent } from '@/api/eventWrites';
import { useAuthStore } from '@/auth/store';
import { useConfirm } from '@/components/ui/useConfirm';
import type { Event } from '@/models/event';
import { EventStatus, EventType } from '@/models/event';

import { EmailBlastDialog } from './EmailBlastDialog';
import { canEditEvent } from './eventEditGate';
import { GroupTextDialog } from './GroupTextDialog';
import { hasQuestionHistory } from './rsvpQuestions';

interface Props {
  event: Event;
  eventHasEnded: boolean;
  canManageRsvps: boolean;
  showSpeech: boolean;
}

export function EventDetailKebabMenu({ event, eventHasEnded, canManageRsvps, showSpeech }: Props) {
  const eventId = event.id;
  const [open, setOpen] = useState(false);
  const [emailBlastOpen, setEmailBlastOpen] = useState(false);
  const [groupTextOpen, setGroupTextOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const user = useAuthStore((s) => s.user);
  const showCheckInReport = canManageRsvps && eventHasEnded;
  const showFeedback = canManageRsvps && eventHasEnded && event.eventType !== EventType.Community;
  const showQuestionResponses = canManageRsvps && hasQuestionHistory(event);
  const showEmailBlast =
    canManageRsvps && event.status !== EventStatus.Draft && event.guests.length > 0;
  const showEdit = canEditEvent(event, user);
  const showRsvpsToggle =
    canManageRsvps && event.rsvpEnabled && event.status === EventStatus.Active && !event.isPast;
  const rsvpsToggle = useRsvpsClosedToggle(event);

  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-label="event settings"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => {
          setOpen((v) => !v);
        }}
        className="bg-surface-dim text-foreground-secondary hover:bg-surface-dim/70 hover:text-foreground inline-flex h-9 w-9 items-center justify-center rounded-md transition-colors"
      >
        <KebabIcon />
      </button>
      {open ? (
        <div
          role="menu"
          className="border-border bg-surface absolute right-0 z-10 mt-1 w-44 overflow-hidden rounded-md border text-sm shadow-lg"
        >
          {showEdit ? (
            <MenuLink
              to={`/events/${eventId}/edit`}
              onSelect={() => {
                setOpen(false);
              }}
            >
              edit
            </MenuLink>
          ) : null}
          {showSpeech ? (
            <MenuLink
              to={`/events/${eventId}/speech`}
              onSelect={() => {
                setOpen(false);
              }}
            >
              event speech
            </MenuLink>
          ) : null}
          {canManageRsvps ? (
            <MenuLink
              to={`/events/${eventId}/manage-rsvps`}
              onSelect={() => {
                setOpen(false);
              }}
            >
              manage rsvps
            </MenuLink>
          ) : null}
          {showQuestionResponses ? (
            <MenuLink
              to={`/events/${eventId}/responses`}
              onSelect={() => {
                setOpen(false);
              }}
            >
              question responses
            </MenuLink>
          ) : null}
          {canManageRsvps ? (
            <MenuLink
              to={`/events/${eventId}/check-in`}
              onSelect={() => {
                setOpen(false);
              }}
            >
              check-in
            </MenuLink>
          ) : null}
          {showCheckInReport ? (
            <MenuLink
              to={`/events/${eventId}/report`}
              onSelect={() => {
                setOpen(false);
              }}
            >
              check-in report
            </MenuLink>
          ) : null}
          {showFeedback ? (
            <MenuLink
              to={`/events/${eventId}/feedback`}
              onSelect={() => {
                setOpen(false);
              }}
            >
              feedback
            </MenuLink>
          ) : null}
          {showEmailBlast ? (
            <MenuButton
              onSelect={() => {
                setOpen(false);
                setEmailBlastOpen(true);
              }}
            >
              email blast
            </MenuButton>
          ) : null}
          {canManageRsvps ? (
            <MenuButton
              onSelect={() => {
                setOpen(false);
                setGroupTextOpen(true);
              }}
            >
              group text
            </MenuButton>
          ) : null}
          {showRsvpsToggle ? (
            <MenuButton
              onSelect={() => {
                setOpen(false);
                void rsvpsToggle.toggle();
              }}
            >
              {event.rsvpsClosed ? 'reopen rsvps' : 'close rsvps'}
            </MenuButton>
          ) : null}
        </div>
      ) : null}
      <EmailBlastDialog
        event={event}
        open={emailBlastOpen}
        onClose={() => {
          setEmailBlastOpen(false);
        }}
      />
      <GroupTextDialog
        eventId={eventId}
        open={groupTextOpen}
        onClose={() => {
          setGroupTextOpen(false);
        }}
      />
      {rsvpsToggle.element}
    </div>
  );
}

function useRsvpsClosedToggle(event: Event) {
  const update = useUpdateEvent(event.id);
  const { confirm, element } = useConfirm();

  async function toggle() {
    const closing = !event.rsvpsClosed;
    if (closing) {
      const ok = await confirm({
        title: 'close rsvps',
        message:
          "no one new can rsvp or join the waitlist, and cancellations won't open spots. you can reopen anytime.",
        confirmLabel: 'close rsvps',
      });
      if (!ok) return;
    }
    update.mutate(
      { rsvpsClosed: closing },
      {
        onError: (err) => {
          toast.error(extractApiErrorOr(err, "couldn't update rsvps — try again"));
        },
      },
    );
  }

  return { toggle, element };
}

function MenuLink({
  to,
  onSelect,
  children,
}: {
  to: string;
  onSelect: () => void;
  children: string;
}) {
  return (
    <Link
      to={to}
      role="menuitem"
      className="text-foreground hover:bg-surface-dim block px-3 py-2"
      onClick={onSelect}
    >
      {children}
    </Link>
  );
}

function MenuButton({ onSelect, children }: { onSelect: () => void; children: string }) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onSelect}
      className="text-foreground hover:bg-surface-dim block w-full px-3 py-2 text-left"
    >
      {children}
    </button>
  );
}

function KebabIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <circle cx="12" cy="5" r="1.6" />
      <circle cx="12" cy="12" r="1.6" />
      <circle cx="12" cy="19" r="1.6" />
    </svg>
  );
}
