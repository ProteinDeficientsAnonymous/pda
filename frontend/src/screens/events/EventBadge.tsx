import type { ReactNode } from 'react';

import { type Event, EventStatus, EventType, EventVisibility } from '@/models/event';

interface Props {
  event: Event;
}

export function EventBadge({ event }: Props) {
  if (event.status === EventStatus.Cancelled) {
    return <Badge tone="neutral">cancelled</Badge>;
  }
  if (event.eventType === EventType.Official) {
    return <Badge tone="blue">official</Badge>;
  }
  if (event.eventType === EventType.Club) {
    return <Badge tone="rose">pda club</Badge>;
  }
  if (event.visibility === EventVisibility.InviteOnly) {
    return <Badge tone="lavender">invite only</Badge>;
  }
  if (event.visibility === EventVisibility.MembersOnly) {
    return <Badge tone="amber">members only</Badge>;
  }
  return null;
}

function Badge({
  tone,
  children,
}: {
  tone: 'neutral' | 'blue' | 'amber' | 'lavender' | 'rose';
  children: ReactNode;
}) {
  const tones = {
    neutral: 'bg-surface-dim text-foreground-secondary',
    blue: 'bg-info-subtle text-info',
    amber: 'bg-warning-subtle text-warning',
    lavender: 'bg-highlight-subtle text-highlight',
    rose: '',
  };
  const style =
    tone === 'rose'
      ? { background: 'var(--color-evt-club-bg)', color: 'var(--color-evt-club-fg)' }
      : undefined;

  return (
    <span className={`rounded-full px-2 py-0.5 text-xs ${tones[tone]}`} style={style}>
      {children}
    </span>
  );
}
