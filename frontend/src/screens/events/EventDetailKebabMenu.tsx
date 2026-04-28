// Host-only kebab menu rendered next to the event title. Items navigate to
// dedicated pages rather than opening modals — keeps the detail page tidy and
// gives each setting room to breathe.

import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

interface Props {
  eventId: string;
}

export function EventDetailKebabMenu({ eventId }: Props) {
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
          <Link
            to={`/events/${eventId}/attendance`}
            role="menuitem"
            className="text-foreground hover:bg-surface-dim block px-3 py-2"
            onClick={() => {
              setOpen(false);
            }}
          >
            attendance
          </Link>
        </div>
      ) : null}
    </div>
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
