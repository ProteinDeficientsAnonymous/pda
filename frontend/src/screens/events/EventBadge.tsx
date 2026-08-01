import { type Event, EventStatus, EventType, EventVisibility } from '@/models/event';

interface Props {
  event: Event;
  onCard?: boolean;
}

type Tone = 'neutral' | 'blue' | 'amber' | 'lavender' | 'rose';

const TONE_CLASS: Record<Tone, string> = {
  neutral: 'bg-surface-dim text-foreground-secondary',
  blue: 'bg-info-subtle text-info',
  amber: 'bg-warning-subtle text-warning',
  lavender: 'bg-highlight-subtle text-highlight',
  rose: '',
};

function badgeFor(event: Event): { tone: Tone; label: string } | null {
  if (event.status === EventStatus.Cancelled) return { tone: 'neutral', label: 'cancelled' };
  if (event.eventType === EventType.Official) return { tone: 'blue', label: 'official' };
  if (event.eventType === EventType.Club) return { tone: 'rose', label: 'pda club' };
  if (event.visibility === EventVisibility.InviteOnly)
    return { tone: 'lavender', label: 'invite only' };
  if (event.visibility === EventVisibility.MembersOnly)
    return { tone: 'amber', label: 'members only' };
  return null;
}

export function EventBadge({ event, onCard = false }: Props) {
  const badge = badgeFor(event);
  if (!badge) return null;

  // On a pda-evt card the pill would sit on the same --color-evt-*-bg it uses,
  // making it invisible. A translucent overlay reads against any card tone.
  if (onCard) {
    return (
      <span className="rounded-full bg-black/10 px-2 py-0.5 text-xs dark:bg-white/15">
        {badge.label}
      </span>
    );
  }

  const style =
    badge.tone === 'rose'
      ? { background: 'var(--color-evt-club-bg)', color: 'var(--color-evt-club-fg)' }
      : undefined;

  return (
    <span className={`rounded-full px-2 py-0.5 text-xs ${TONE_CLASS[badge.tone]}`} style={style}>
      {badge.label}
    </span>
  );
}
