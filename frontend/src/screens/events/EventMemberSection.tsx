import { useState } from 'react';
import { Link } from 'react-router-dom';

import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import type { Event } from '@/models/event';
import { EventStatus, InvitePermission, RsvpStatus } from '@/models/event';
import { hasPermission } from '@/models/permissions';
import { Permission } from '@/models/permissions';
import { buildEventLinks } from '@/utils/eventLinks';
import { ensureHttps } from '@/utils/url';

import { EventCommentsCard } from './comments/EventCommentsCard';
import { EmailBlastButton } from './EmailBlastButton';
import { EventAdminActions } from './EventAdminActions';
import { Card } from './EventDetailCard';
import { EventFlagDialog } from './EventFlagDialog';
import { EventHostSection } from './EventHostSection';
import { GroupTextButton } from './GroupTextButton';
import { InviteDialog } from './InviteDialog';
import { InvitedList } from './RsvpGuestList';
import { RsvpSection } from './RsvpSection';

interface Props {
  event: Event;
  token?: string;
}

// A token holder has no real member identity — resolve_event_viewer explicitly
// never satisfies member/creator/co-host checks for a token (see backend
// community/_event_viewer.py). Host/admin affordances stay gated on the real
// auth session, never on the token.
export function EventMemberSection({ event, token }: Props) {
  const user = useAuthStore((s) => s.user);
  if (!user && !token) return null;

  // A token holder is never a real member — resolve_event_viewer explicitly
  // never satisfies member/creator/co-host checks for a token (see backend
  // community/_event_viewer.py). Host/invite/admin affordances all key off
  // a real auth session, never the token.
  const isCoHost =
    user !== null && (user.id === event.createdById || event.coHostIds.includes(user.id));
  const canManageEvents = user !== null && hasPermission(user, Permission.ManageEvents);
  const canSeeInvited = isCoHost || canManageEvents;
  const isCancelled = event.status === EventStatus.Cancelled;
  const rsvpDisabled = !event.rsvpEnabled;
  const hasRsvpd = event.myRsvp === RsvpStatus.Attending || event.myRsvp === RsvpStatus.Maybe;
  const canInvite =
    user !== null &&
    !isCancelled &&
    !event.isPast &&
    !rsvpDisabled &&
    (isCoHost ||
      canManageEvents ||
      (event.invitePermission === InvitePermission.AllMembers && hasRsvpd));
  const showRsvp = !event.isPast && event.rsvpEnabled && event.status !== EventStatus.Cancelled;
  const showStandaloneInvited = !showRsvp && canSeeInvited && event.invitedCount > 0;

  return (
    <div className="mt-8 flex flex-col gap-6">
      {user ? (
        <EventHostSection
          event={event}
          canEdit={isCoHost && !isCancelled}
          canInviteCohost={isCoHost && !isCancelled && !event.isPast}
          viewerId={user.id}
        />
      ) : null}
      <LocationSection event={event} />
      <LinksSection event={event} />
      <CostSection event={event} />
      {showRsvp ? (
        <Card label="rsvp">
          <RsvpSection event={event} canSeeInvited={canSeeInvited} {...(token ? { token } : {})} />
          {canInvite || isCoHost ? (
            <div className="mt-4 flex flex-wrap justify-end gap-2">
              {canInvite ? <InviteSection event={event} /> : null}
              {isCoHost ? (
                <>
                  <EmailBlastButton event={event} />
                  <GroupTextButton event={event} />
                </>
              ) : null}
            </div>
          ) : null}
        </Card>
      ) : null}
      {showStandaloneInvited ? (
        <Card label="invited">
          <InvitedList event={event} />
        </Card>
      ) : null}
      {rsvpDisabled ? null : <EventCommentsCard eventId={event.id} {...(token ? { token } : {})} />}
      <EventAdminActions event={event} />
      <ReportEventButton eventId={event.id} />
    </div>
  );
}

function ReportEventButton({ eventId }: { eventId: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="flex justify-center pt-2">
      <Button
        variant="ghost"
        className="text-xs text-neutral-500"
        onClick={() => {
          setOpen(true);
        }}
      >
        report this event
      </Button>
      <EventFlagDialog
        eventId={eventId}
        open={open}
        onClose={() => {
          setOpen(false);
        }}
      />
    </div>
  );
}

export function LocationSection({ event }: { event: Event }) {
  if (!event.location) return null;
  const primary = event.location.split(', ')[0] ?? event.location;
  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(event.location)}`;
  return (
    <Card label="location">
      <a
        href={mapsUrl}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={`open ${event.location} in maps`}
        className="text-brand-700 hover:text-brand-900 text-sm"
      >
        {primary}
      </a>
    </Card>
  );
}

export function LinksSection({ event }: { event: Event }) {
  const links = buildEventLinks(event);
  const feedbackSurveys = event.surveySlugs.filter((s) => s !== event.datetimePollSlug);

  if (links.length === 0 && feedbackSurveys.length === 0) return null;
  return (
    <Card label="links">
      <ul className="flex flex-col gap-2 text-sm">
        {links.map((l) => (
          <li key={l.url}>
            <a
              href={l.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-700 hover:text-brand-900"
            >
              {l.label}
            </a>
          </li>
        ))}
        {feedbackSurveys.map((slug) => (
          <li key={slug}>
            <Link to={`/surveys/${slug}`} className="text-brand-700 hover:text-brand-900">
              give feedback
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function CostSection({ event }: { event: Event }) {
  const items: { label: string; url?: string }[] = [];
  if (event.price) items.push({ label: formatPrice(event.price) });
  if (event.venmoLink) items.push({ label: 'venmo', url: ensureHttps(event.venmoLink) });
  if (event.cashappLink) items.push({ label: 'cashapp', url: ensureHttps(event.cashappLink) });
  if (event.zelleInfo) items.push({ label: `zelle: ${event.zelleInfo}` });
  if (items.length === 0) return null;
  return (
    <Card label="cost">
      <ul className="flex flex-col gap-2 text-sm">
        {items.map((item) => (
          <li key={item.label}>
            {item.url ? (
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-brand-700 hover:text-brand-900"
              >
                {item.label}
              </a>
            ) : (
              <span className="text-foreground">{item.label}</span>
            )}
          </li>
        ))}
      </ul>
    </Card>
  );
}

// "free" stays bare. Anything that starts with a digit gets "$" prepended
// unless the user already typed one. Anything else (e.g. "sliding scale")
// passes through as-written.
function formatPrice(price: string): string {
  const trimmed = price.trim();
  if (!trimmed) return trimmed;
  if (/^\$/.test(trimmed)) return trimmed;
  if (/^\d/.test(trimmed)) return `$${trimmed}`;
  return trimmed;
}

function InviteSection({ event }: { event: Event }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        variant="secondary"
        onClick={() => {
          setOpen(true);
        }}
      >
        invite members
      </Button>
      <InviteDialog
        event={event}
        open={open}
        onClose={() => {
          setOpen(false);
        }}
      />
    </>
  );
}
