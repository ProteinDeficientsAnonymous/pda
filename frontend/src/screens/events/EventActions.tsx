// Action row on the event detail page: add-to-calendar menu + share.
//
// Add-to-calendar is a tiny popover with google / apple / download-ics.
// Share uses the Web Share API when available; falls back to clipboard.

import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import type { Event } from '@/models/event';
import { googleCalendarUrl, icsUrl, webcalUrl, shareEventUrl } from '@/utils/eventCalendar';

interface Props {
  event: Event;
}

export function EventActions({ event }: Props) {
  const showCalendar = !event.isPast && !!event.startDatetime;
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      {showCalendar ? <CalendarMenu event={event} /> : null}
      <ShareButton event={event} />
    </div>
  );
}

function ShareButton({ event }: { event: Event }) {
  return (
    <IconChip
      label="share event"
      onClick={() => {
        void shareEventUrl(event)
          .then(() => {
            if (typeof window.navigator.share !== 'function') {
              toast.success('link copied');
            }
          })
          .catch(() => {
            toast.error("couldn't share — try again");
          });
      }}
    >
      <ShareIcon />
    </IconChip>
  );
}

function CalendarMenu({ event }: { event: Event }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

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

  const google = googleCalendarUrl(event);
  return (
    <div ref={rootRef} className="relative">
      <IconChip
        label="add to calendar"
        onClick={() => {
          setOpen((v) => !v);
        }}
        aria-expanded={open}
      >
        <CalendarPlusIcon />
      </IconChip>
      {open ? (
        <div
          role="menu"
          className="border-border bg-surface absolute left-0 z-10 mt-1 w-44 overflow-hidden rounded-md border text-sm shadow-lg"
        >
          {google ? (
            <a
              href={google}
              target="_blank"
              rel="noopener noreferrer"
              role="menuitem"
              className="text-foreground hover:bg-surface-dim block px-3 py-2"
              onClick={() => {
                setOpen(false);
              }}
            >
              google calendar
            </a>
          ) : null}
          <a
            href={webcalUrl(event.id)}
            role="menuitem"
            className="text-foreground hover:bg-surface-dim block px-3 py-2"
            onClick={() => {
              setOpen(false);
            }}
          >
            apple calendar
          </a>
          <a
            href={icsUrl(event.id)}
            download={`${event.title}.ics`}
            role="menuitem"
            className="text-foreground hover:bg-surface-dim block px-3 py-2"
            onClick={() => {
              setOpen(false);
            }}
          >
            download .ics
          </a>
        </div>
      ) : null}
    </div>
  );
}

interface IconChipProps {
  label: string;
  children: React.ReactNode;
  onClick: () => void;
  'aria-expanded'?: boolean;
}

function IconChip({ label, children, onClick, ...rest }: IconChipProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className="bg-surface-dim text-foreground-secondary hover:bg-surface-dim/70 hover:text-foreground inline-flex h-9 w-9 items-center justify-center rounded-md transition-colors"
      {...rest}
    >
      {children}
    </button>
  );
}

function ShareIcon() {
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
      <circle cx="18" cy="5" r="3" />
      <circle cx="6" cy="12" r="3" />
      <circle cx="18" cy="19" r="3" />
      <path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4" />
    </svg>
  );
}

function CalendarPlusIcon() {
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
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M8 3v4M16 3v4M3 10h18M12 14v4M10 16h4" />
    </svg>
  );
}
