import { Link, useParams } from 'react-router-dom';

import { extractApiError, getApiStatus } from '@/api/apiErrors';
import { useEvent } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import { canManageEvent } from '@/models/event';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { EventForbiddenNotice } from './EventForbiddenNotice';
import { EventManageRsvpsPanel } from './EventManageRsvpsPanel';

export default function EventManageRsvpsScreen() {
  const { id } = useParams<{ id: string }>();
  const user = useAuthStore((s) => s.user);
  const { data: event, isPending, isError, error } = useEvent(id);

  if (isPending) return <ContentLoading />;
  if (isError) {
    if (getApiStatus(error) === 403) {
      const message = extractApiError(error) ?? "you don't have permission to see this event";
      return <EventForbiddenNotice eventId={id} message={message} />;
    }
    return <ContentError message="couldn't load this event — try refreshing" />;
  }

  if (!canManageEvent(event, user)) {
    return (
      <EventForbiddenNotice
        eventId={event.id}
        message="only the host or a co-host can manage rsvps"
      />
    );
  }
  if (!event.rsvpEnabled) {
    return (
      <EventForbiddenNotice
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
      {event.isPast ? <PastEventNote eventId={event.id} /> : null}
      <EventManageRsvpsPanel event={event} />
    </ContentContainer>
  );
}

function PastEventNote({ eventId }: { eventId: string }) {
  return (
    <p className="border-border bg-surface text-foreground-secondary mb-6 rounded-md border p-3 text-sm">
      this event already happened — anyone you add counts as going. mark who showed up on{' '}
      <Link to={`/events/${eventId}/check-in`} className="text-foreground underline">
        check-in
      </Link>
    </p>
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
