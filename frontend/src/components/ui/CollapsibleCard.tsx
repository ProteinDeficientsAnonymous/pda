// Expand/collapse card for grouped form sections.
//
// - Header is a real <button> toggling aria-expanded + aria-controls on the
//   panel. Chevron animates via CSS transform.
// - `forceOpen` overrides local state — used by the event form to open any
//   section that has a validation error on submit.
// - `summary` slot appears on the right when collapsed (e.g. "3 links" /
//   "members only"). Hidden when an error is present.
//
// Reusable anywhere we want a "cute, friendly" expandable block.

import { useId, useState, type ReactNode } from 'react';
import { cn } from '@/utils/cn';

interface Props {
  title: string;
  /** Decorative leading emoji/icon shown on the header. */
  emoji?: string;
  /** Shown on the right of the header when collapsed and no error present. */
  summary?: ReactNode;
  /** Displayed as a red chip on the right when present (e.g. "1 issue"). */
  error?: ReactNode;
  /** Start expanded. Ignored when `forceOpen` is true. */
  defaultOpen?: boolean;
  /** Pin open regardless of user interaction. */
  forceOpen?: boolean;
  children: ReactNode;
}

export function CollapsibleCard({
  title,
  emoji,
  summary,
  error,
  defaultOpen = false,
  forceOpen = false,
  children,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();
  const isOpen = forceOpen || open;

  return (
    <section
      className={cn(
        'overflow-hidden rounded-[var(--radius-md)] border bg-surface shadow-(--shadow-sm) transition-colors',
        isOpen ? 'border-brand-200' : 'border-brand-100 hover:border-brand-200',
      )}
    >
      <button
        type="button"
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={() => {
          if (!forceOpen) setOpen((v) => !v);
        }}
        className="focus-visible:ring-brand-200 hover:bg-brand-50/50 flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors focus-visible:ring-2 focus-visible:outline-none"
      >
        <span className="flex items-center gap-2">
          {emoji ? (
            <span aria-hidden="true" className="text-base">
              {emoji}
            </span>
          ) : null}
          <span className="text-sm font-medium text-foreground">{title}</span>
        </span>
        <span className="flex items-center gap-2">
          {error ? (
            <span className="rounded-full bg-destructive-subtle px-2 py-0.5 text-xs font-medium text-destructive">
              {error}
            </span>
          ) : !isOpen && summary ? (
            <span className="bg-brand-100 text-brand-800 rounded-full px-2 py-0.5 text-xs font-medium">
              {summary}
            </span>
          ) : null}
          <Chevron open={isOpen} />
        </span>
      </button>
      <div
        id={panelId}
        role="region"
        aria-labelledby={undefined}
        hidden={!isOpen}
        className="border-brand-100 border-t px-4 py-4"
      >
        {children}
      </div>
    </section>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={cn('text-muted transition-transform duration-200', open && 'rotate-180')}
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}
