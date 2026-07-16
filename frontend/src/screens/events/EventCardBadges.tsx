import { type Event, myRsvpLabel } from '@/models/event';
import { cn } from '@/utils/cn';

type Variant = 'card' | 'row';

const PILL_CLASS: Record<Variant, string> = {
  card: 'rounded-full bg-black/10 px-2 py-0.5 dark:bg-white/15',
  row: 'rounded-full bg-surface-dim text-foreground-secondary px-2 py-0.5',
};

function headcountLabel(event: Event): string | null {
  if (event.maxAttendees === null) return null;
  // Matches the spacing of the detail-panel summary ("n / max going").
  return `${String(event.attendingCount)} / ${String(event.maxAttendees)} going`;
}

export function EventCardBadges({
  event,
  variant,
  className,
}: {
  event: Event;
  variant: Variant;
  className?: string;
}) {
  const rsvp = myRsvpLabel(event);
  const headcount = headcountLabel(event);

  if (!rsvp && !headcount) return null;

  const pill = PILL_CLASS[variant];

  return (
    <div className={cn('flex flex-wrap items-center gap-1.5 text-xs', className)}>
      {rsvp ? <span className={cn(pill, 'font-medium')}>{rsvp}</span> : null}
      {headcount ? <span className={pill}>{headcount}</span> : null}
    </div>
  );
}