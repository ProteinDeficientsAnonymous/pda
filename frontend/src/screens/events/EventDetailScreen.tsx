import { Link, useParams } from 'react-router-dom';
import { useEvent } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import { EventStatus, EventType, EventVisibility } from '@/models/event';
import { formatEventDateTime } from '@/utils/datetime';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { EventMemberSection } from './EventMemberSection';
import { EventPollCard } from './poll/EventPollCard';

export default function EventDetailScreen() {
  const { id } = useParams<{ id: string }>();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  const { data: event, isPending, isError } = useEvent(id);

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load this event — try refreshing" />;

  return (
    <ContentContainer>
      {event.photoUrl ? (
        <img
          src={event.photoUrl}
          alt=""
          className="mb-4 aspect-video w-full rounded-lg object-cover"
          loading="lazy"
        />
      ) : null}

      <div className="mb-2 flex flex-wrap items-center gap-2">
        <h1 className="text-2xl font-medium tracking-tight">{event.title}</h1>
        <VisibilityBadge event={event} />
      </div>

      <WhenLine event={event} />
      <EventPollCard event={event} />

      {event.description ? (
        <section className="mt-6">
          <h2 className="mb-2 text-sm font-medium text-muted">about</h2>
          <p className="whitespace-pre-wrap text-foreground">{event.description}</p>
        </section>
      ) : null}

      {isAuthed ? <EventMemberSection event={event} /> : <LoginOrJoinSection />}
    </ContentContainer>
  );
}

// Hides the normal datetime line while a poll is active (no start time yet).
// Once finalized the backend sets startDatetime; we're back to normal.
// For a no-poll event, EventPollCard owns the "tbd + propose dates" line
// for hosts, so we suppress the plain "tbd" to avoid showing it twice.
function WhenLine({ event }: { event: Event }) {
  const user = useAuthStore((s) => s.user);
  const pollActive = event.hasPoll && !event.startDatetime;
  const isHost = !!user && (user.id === event.createdById || event.coHostIds.includes(user.id));
  const hostWillProposeDates = !event.hasPoll && !event.startDatetime && isHost;
  if (pollActive || hostWillProposeDates) return null;
  return (
    <p className="text-sm text-foreground-secondary">
      {event.startDatetime
        ? formatEventDateTime(event.startDatetime, event.endDatetime, event.datetimeTbd)
        : 'date & time tbd'}
    </p>
  );
}

function VisibilityBadge({ event }: { event: Event }) {
  if (event.status === EventStatus.Cancelled) {
    return <Badge tone="neutral">cancelled</Badge>;
  }
  if (event.eventType === EventType.Official) {
    return <Badge tone="blue">official</Badge>;
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
  tone: 'neutral' | 'blue' | 'amber' | 'lavender';
  children: React.ReactNode;
}) {
  const tones = {
    neutral: 'bg-surface-dim text-foreground-secondary',
    blue: 'bg-info-subtle text-info',
    amber: 'bg-warning-subtle text-warning',
    lavender: 'bg-highlight-subtle text-highlight',
  };
  return <span className={`rounded-full px-2 py-0.5 text-xs ${tones[tone]}`}>{children}</span>;
}

function LoginOrJoinSection() {
  // Unauthed users miss: hosts, location, links, cost, invite, RSVP.
  return (
    <section className="mt-8 rounded-lg border border-border bg-surface p-6">
      <h2 className="mb-2 text-base font-medium">want to see more?</h2>
      <p className="mb-4 text-sm text-foreground-tertiary">
        location, rsvp, and organizer details are shown once you sign in
      </p>
      <div className="flex flex-wrap gap-3">
        <Link
          to="/login"
          className="inline-flex h-10 items-center rounded-md bg-brand-600 px-4 text-sm font-medium text-brand-on hover:bg-brand-700"
        >
          sign in
        </Link>
        <Link
          to="/join"
          className="inline-flex h-10 items-center rounded-md border border-border-strong px-4 text-sm font-medium text-foreground-secondary hover:bg-background"
        >
          request to join
        </Link>
      </div>
    </section>
  );
}
