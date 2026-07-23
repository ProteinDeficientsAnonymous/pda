import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import { useFlag } from '@/api/featureFlags';
import type { Event } from '@/models/event';
import { EventStatus } from '@/models/event';
import { Feature } from '@/models/featureFlags';

import { EmailBlastDialog } from './EmailBlastDialog';
import { GroupTextDialog } from './GroupTextDialog';

interface Props {
  event: Event;
  eventHasEnded: boolean;
  canManageRsvps: boolean;
}

export function EventDetailKebabMenu({ event, eventHasEnded, canManageRsvps }: Props) {
  const eventId = event.id;
  const [open, setOpen] = useState(false);
  const [emailBlastOpen, setEmailBlastOpen] = useState(false);
  const [groupTextOpen, setGroupTextOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const reportFlagOn = useFlag(Feature.HostAttendanceReport);
  const showCheckInReport = eventHasEnded && reportFlagOn;
  const showManageRsvps = canManageRsvps && !eventHasEnded;
  const showEmailBlast = event.status !== EventStatus.Draft && event.guests.length > 0;

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
          {showManageRsvps ? (
            <MenuLink
              to={`/events/${eventId}/manage-rsvps`}
              onSelect={() => {
                setOpen(false);
              }}
            >
              manage rsvps
            </MenuLink>
          ) : null}
          <MenuLink
            to={`/events/${eventId}/attendance`}
            onSelect={() => {
              setOpen(false);
            }}
          >
            check-in
          </MenuLink>
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
          <MenuButton
            onSelect={() => {
              setOpen(false);
              setGroupTextOpen(true);
            }}
          >
            group text
          </MenuButton>
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
    </div>
  );
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
