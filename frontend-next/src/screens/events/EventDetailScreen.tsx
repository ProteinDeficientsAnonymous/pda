import { Link, useParams } from 'react-router-dom';
import { useEvent } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import { EventStatus, EventType, EventVisibility } from '@/models/event';
import { formatEventDateTime } from '@/utils/datetime';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { EventMemberSection } from './EventMemberSection';

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

      <p className="text-sm text-neutral-700">
        {formatEventDateTime(event.startDatetime, event.endDatetime, event.datetimeTbd)}
      </p>

      {event.description ? (
        <section className="mt-6">
          <h2 className="mb-2 text-sm font-medium text-neutral-500">about</h2>
          <p className="whitespace-pre-wrap text-neutral-800">{event.description}</p>
        </section>
      ) : null}

      {isAuthed ? <EventMemberSection event={event} /> : <LoginOrJoinSection />}
    </ContentContainer>
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
    neutral: 'bg-neutral-100 text-neutral-700',
    blue: 'bg-blue-100 text-blue-900',
    amber: 'bg-amber-100 text-amber-900',
    lavender: 'bg-purple-100 text-purple-900',
  };
  return <span className={`rounded-full px-2 py-0.5 text-xs ${tones[tone]}`}>{children}</span>;
}

function LoginOrJoinSection() {
  // Unauthed users miss: hosts, location, links, cost, invite, RSVP.
  return (
    <section className="mt-8 rounded-lg border border-neutral-200 bg-white p-6">
      <h2 className="mb-2 text-base font-medium">want to see more?</h2>
      <p className="mb-4 text-sm text-neutral-600">
        location, rsvp, and organizer details are shown once you sign in
      </p>
      <div className="flex flex-wrap gap-3">
        <Link
          to="/login"
          className="inline-flex h-10 items-center rounded-md bg-neutral-900 px-4 text-sm font-medium text-white hover:bg-neutral-800"
        >
          sign in
        </Link>
        <Link
          to="/join"
          className="inline-flex h-10 items-center rounded-md border border-neutral-300 px-4 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
        >
          request to join
        </Link>
      </div>
    </section>
  );
}
