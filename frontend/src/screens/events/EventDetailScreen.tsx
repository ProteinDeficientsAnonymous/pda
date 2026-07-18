import { Link, useParams, useSearchParams } from 'react-router-dom';

import { extractApiError, getApiStatus } from '@/api/apiErrors';
import { useEvent } from '@/api/events';
import { getStoredRsvpToken } from '@/api/rsvpTokenStorage';
import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import { canManageEvent, canPublicRsvp } from '@/models/event';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { formatEventDateTime } from '@/utils/datetime';
import { linkifyText } from '@/utils/linkifyText';

import { CohostInviteBanner } from './CohostInviteBanner';
import { EventActions } from './EventActions';
import { EventBadge } from './EventBadge';
import { EventDetailKebabMenu } from './EventDetailKebabMenu';
import { EventMemberSection } from './EventMemberSection';
import { EventTagChips } from './EventTagChips';
import { EventPollCard } from './poll/EventPollCard';
import { PublicRsvpSection } from './PublicRsvpSection';

function photoSrc(url: string, updatedAt: string | null): string {
  if (!updatedAt) return url;
  return `${url}?v=${encodeURIComponent(updatedAt)}`;
}

export default function EventDetailScreen() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  const user = useAuthStore((s) => s.user);
  // The emailed link carries ?rsvp_token=…; a returning non-member arrives with
  // none, so fall back to the token persisted on their last rsvp (issue #873).
  const urlToken = searchParams.get('rsvp_token') ?? undefined;
  const rsvpToken = isAuthed ? undefined : (urlToken ?? getStoredRsvpToken() ?? undefined);
  const { data: event, isPending, isError, error } = useEvent(id, undefined, rsvpToken);

  // We never clear the stored token here: viewerUserId is null both for a dead
  // token AND for a live token on an event that isn't public-rsvp-eligible, so
  // this view can't tell them apart. Clearing on that ambiguous signal wiped
  // valid tokens mid-browse (issue #880). A dead token is harmless — it resolves
  // to anonymous — and is cleared authoritatively by the /my-rsvps 404 path.

  if (isPending) return <ContentLoading />;
  if (isError) {
    if (getApiStatus(error) === 403) {
      const message = extractApiError(error) ?? "you don't have permission to see this event";
      return <ForbiddenNotice message={message} />;
    }
    return <ContentError message="couldn't load this event — try refreshing" />;
  }

  const showKebab = isAuthed && event.rsvpEnabled && canManageEvent(event, user);
  // viewerUserId is set by the backend's viewer resolver only when the caller
  // resolved to a real identity (member, or a valid token on an eligible event);
  // an invalid/expired token gets the same locked shape as no token at all, so
  // this is an exact backend-verified signal, not a guess.
  const hasTokenUnlock = Boolean(rsvpToken) && !isAuthed && event.viewerUserId !== null;

  return (
    <ContentContainer>
      {event.photoUrl ? (
        <img
          src={photoSrc(event.photoUrl, event.photoUpdatedAt)}
          alt=""
          className="mx-auto mb-4 block max-h-[70vh] w-auto max-w-full rounded-lg"
          loading="lazy"
        />
      ) : null}

      <div className="mb-2 flex flex-wrap items-center gap-2">
        <h1 className="text-2xl font-medium tracking-tight [overflow-wrap:anywhere] break-words">
          {event.title}
        </h1>
        <EventBadge event={event} />
        {showKebab ? (
          <div className="ml-auto">
            <EventDetailKebabMenu eventId={event.id} />
          </div>
        ) : null}
      </div>

      <WhenLine event={event} />
      <EventTagChips tags={event.tags} className="mt-2" />
      <EventActions event={event} />
      {isAuthed ? <CohostInviteBanner event={event} /> : null}
      <EventPollCard event={event} />

      {event.description ? (
        <section className="mt-6">
          <h2 className="text-muted mb-2 text-sm font-medium">about</h2>
          <p className="text-foreground [overflow-wrap:anywhere] break-words whitespace-pre-wrap">
            {linkifyText(event.description)}
          </p>
        </section>
      ) : null}

      <DetailSection
        event={event}
        isAuthed={isAuthed}
        hasTokenUnlock={hasTokenUnlock}
        rsvpToken={rsvpToken}
      />
    </ContentContainer>
  );
}

// Hides the normal datetime line while a poll is active (no start time yet).
// Once finalized the backend sets startDatetime; we're back to normal.
function WhenLine({ event }: { event: Event }) {
  const pollActive = event.hasPoll && !event.startDatetime;
  if (pollActive) return null;
  return (
    <p className="text-foreground-secondary text-sm">
      {event.startDatetime
        ? formatEventDateTime(event.startDatetime, event.endDatetime, event.datetimeTbd)
        : 'date & time tbd'}
    </p>
  );
}

function ForbiddenNotice({ message }: { message: string }) {
  return (
    <ContentContainer>
      <section className="border-border bg-surface mt-8 rounded-lg border p-6">
        <h2 className="mb-2 text-base font-medium">{message}</h2>
        <p className="text-foreground-tertiary mb-4 text-sm">
          if you think this is a mistake, reach out to the host
        </p>
        <Link
          to="/calendar"
          className="border-border-strong text-foreground-secondary hover:bg-background inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium"
        >
          back to calendar
        </Link>
      </section>
    </ContentContainer>
  );
}

function DetailSection({
  event,
  isAuthed,
  hasTokenUnlock,
  rsvpToken,
}: {
  event: Event;
  isAuthed: boolean;
  hasTokenUnlock: boolean;
  rsvpToken: string | undefined;
}) {
  if (isAuthed) return <EventMemberSection event={event} />;
  if (hasTokenUnlock) return <EventMemberSection event={event} token={rsvpToken ?? ''} />;
  return <AnonSection event={event} />;
}

function AnonSection({ event }: { event: Event }) {
  if (canPublicRsvp(event)) return <PublicRsvpSection event={event} />;
  return <LoginOrJoinSection />;
}

function LoginOrJoinSection() {
  // Unauthed users miss: hosts, location, links, cost, invite, RSVP.
  return (
    <section className="border-border bg-surface mt-8 rounded-lg border p-6">
      <h2 className="mb-2 text-base font-medium">want to see more?</h2>
      <p className="text-foreground-tertiary mb-4 text-sm">
        location, rsvp, and organizer details are shown once you sign in
      </p>
      <div className="flex flex-wrap gap-3">
        <Link
          to="/login"
          className="bg-brand-600 text-brand-on hover:bg-brand-700 inline-flex h-10 items-center rounded-md px-4 text-sm font-medium"
        >
          sign in
        </Link>
        <Link
          to="/join"
          className="border-border-strong text-foreground-secondary hover:bg-background inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium"
        >
          request to join
        </Link>
      </div>
      <p className="text-foreground-tertiary mt-4 text-sm">
        if you're not a member yet, look for the official events in blue on the calendar — once
        you've come to one of those, you'll be able to sign up for all of the events on here!
      </p>
    </section>
  );
}
