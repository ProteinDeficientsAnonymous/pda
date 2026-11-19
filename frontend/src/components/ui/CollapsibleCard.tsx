import { type ReactNode, useId, useState } from 'react';

import { cn } from '@/utils/cn';

import { Chevron } from './Chevron';

interface Props {
  title: string;
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
        'bg-surface rounded-[var(--radius-md)] border shadow-(--shadow-sm) transition-colors',
        // Clipping an open card would cut off popovers inside it, like the date pickers.
        isOpen ? 'border-brand-200' : 'border-brand-100 hover:border-brand-200 overflow-hidden',
      )}
    >
      <button
        type="button"
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={() => {
          if (!forceOpen) setOpen((v) => !v);
        }}
        className="focus-visible:ring-brand-200 hover:bg-brand-50/50 flex w-full items-center justify-between gap-3 rounded-t-[var(--radius-md)] px-4 py-3 text-left transition-colors focus-visible:ring-2 focus-visible:outline-none"
      >
        <span className="flex items-center gap-2">
          <span className="text-foreground text-sm font-medium">{title}</span>
        </span>
        <span className="flex items-center gap-2">
          {error ? (
            <span className="bg-destructive-subtle text-destructive rounded-full px-2 py-0.5 text-xs font-medium">
              {error}
            </span>
          ) : !isOpen && summary ? (
            <span className="bg-brand-100 text-brand-800 rounded-full px-2 py-0.5 text-xs font-medium">
              {summary}
            </span>
          ) : null}
          <Chevron open={isOpen} className="text-muted" />
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
