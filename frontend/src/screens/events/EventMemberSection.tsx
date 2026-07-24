import { useState } from 'react';
import { Link } from 'react-router-dom';

import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import type { Event } from '@/models/event';
import { spotsLeft } from '@/models/event';
import { buildEventLinks } from '@/utils/eventLinks';
import { ensureHttps } from '@/utils/url';

import { EventCommentsCard } from './comments/EventCommentsCard';
import { EmailBlastButton } from './EmailBlastButton';
import { EventAdminActions } from './EventAdminActions';
import { Card } from './EventDetailCard';
import { EventFlagDialog } from './EventFlagDialog';
import { EventHostSection } from './EventHostSection';
import { eventMemberSectionFlags } from './eventMemberFlags';
import { GroupTextButton } from './GroupTextButton';
import { InviteDialog } from './InviteDialog';
import { InvitedList, RsvpGuestList } from './RsvpGuestList';

interface Props {
  event: Event;
  token?: string;
}

export function EventMemberSection({ event, token }: Props) {
  const user = useAuthStore((s) => s.user);
  if (!user && !token) return null;

  const {
    isCoHost,
    canSeeInvited,
    isCancelled,
    rsvpDisabled,
    canInvite,
    showRsvp,
    showStandaloneInvited,
  } = eventMemberSectionFlags(event, user);

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
        <Card label="who's going">
          <CapacityNote event={event} />
          <RsvpGuestList event={event} canSeeInvited={canSeeInvited} />
          {canInvite || isCoHost ? (
            <div className="mt-4 flex flex-col items-stretch gap-2">
              {canInvite ? <InviteSection event={event} /> : null}
              {isCoHost ? (
                <div className="flex flex-wrap justify-end gap-2">
                  <EmailBlastButton event={event} />
                  <GroupTextButton event={event} />
                </div>
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

function CapacityNote({ event }: { event: Event }) {
  const { maxAttendees } = event;
  const left = spotsLeft(event);
  if (left === null || maxAttendees === null) return null;
  return (
    <p className="text-muted mb-3 -mt-2 text-xs">
      {left}/{maxAttendees} spots left
    </p>
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
