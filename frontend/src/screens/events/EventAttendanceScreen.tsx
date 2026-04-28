// Dedicated host-only page for event attendance — accessed via the kebab menu
// on the event detail screen. Gates the panel behind creator/co-host/manage_events.

import { Link, useParams } from 'react-router-dom';
import { extractApiError, getApiStatus } from '@/api/apiErrors';
import { useEvent } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import { Permission, hasPermission } from '@/models/permissions';
import type { User } from '@/models/user';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { EventAttendancePanel } from './EventAttendancePanel';

export default function EventAttendanceScreen() {
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

  if (!canSeeAttendance(event, user)) {
    return (
      <ForbiddenNotice eventId={event.id} message="only the host or a co-host can see attendance" />
    );
  }

  return (
    <ContentContainer>
      <BackLink eventId={event.id} />
      <h1 className="mb-1 text-2xl font-medium tracking-tight">attendance</h1>
      <p className="text-foreground-secondary mb-6 text-sm">{event.title}</p>
      <EventAttendancePanel event={event} />
    </ContentContainer>
  );
}

function canSeeAttendance(event: Event, user: User | null): boolean {
  if (!user) return false;
  if (user.id === event.createdById) return true;
  if (event.coHostIds.includes(user.id)) return true;
  return hasPermission(user, Permission.ManageEvents);
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
