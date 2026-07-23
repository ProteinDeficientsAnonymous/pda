import { Link, useParams } from 'react-router-dom';

import { extractApiError, getApiStatus } from '@/api/apiErrors';
import { useEvent } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import { canManageEvent } from '@/models/event';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { EventManageRsvpsPanel } from './EventManageRsvpsPanel';

export default function EventManageRsvpsScreen() {
  const { id } = useParams<{ id: string }>();
  const user = useAuthStore((s) => s.user);
  const { data: event, isPending, isError, error } = useEvent(id);

  if (isPending) return <ContentLoading />;
  if (isError) {
    if (getApiStatus(error) === 403) {
      const message = extractApiError(error) ?? "you don't have permission to see this event";
      return <ForbiddenNotice eventId={id} message={message} />;
    }
    return <ContentError message="couldn't load this event — try refreshing" />;
  }

  if (!canManageEvent(event, user)) {
    return (
      <ForbiddenNotice eventId={event.id} message="only the host or a co-host can manage rsvps" />
    );
  }
  if (event.isPast) {
    return <ForbiddenNotice eventId={event.id} message="this event has already happened" />;
  }
  if (!event.rsvpEnabled) {
    return (
      <ForbiddenNotice
        eventId={event.id}
        message="rsvps are off for this event — nothing to manage"
      />
    );
  }

  return (
    <ContentContainer>
      <BackLink eventId={event.id} />
      <h1 className="mb-1 text-2xl font-medium tracking-tight">manage rsvps</h1>
      <p className="text-foreground-secondary mb-6 text-sm">{event.title}</p>
      <EventManageRsvpsPanel event={event} />
    </ContentContainer>
  );
}

function BackLink({ eventId }: { eventId: string }) {
  return (
    <Link
      to={`/events/${eventId}`}
      className="text-foreground-secondary hover:text-foreground mb-4 inline-flex items-center gap-1 text-sm"
    >
      ← back to event
    </Link>
  );
}

function ForbiddenNotice({ eventId, message }: { eventId: string | undefined; message: string }) {
  return (
    <ContentContainer>
      <section className="border-border bg-surface mt-8 rounded-lg border p-6">
        <h2 className="mb-2 text-base font-medium">{message}</h2>
        <Link
          to={eventId ? `/events/${eventId}` : '/calendar'}
          className="border-border-strong text-foreground-secondary hover:bg-background mt-4 inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium"
        >
          back to event
        </Link>
      </section>
    </ContentContainer>
  );
}
