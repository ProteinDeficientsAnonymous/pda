import { useState } from 'react';
import { Link } from 'react-router-dom';

import { useFlag } from '@/api/featureFlags';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import type { Event } from '@/models/event';
import { spotsLeft } from '@/models/event';
import { Feature } from '@/models/featureFlags';
import { formatPrice } from '@/utils/eventCost';
import { buildEventLinks } from '@/utils/eventLinks';
import { toCashAppPayUrl } from '@/utils/paymentHandle';
import { ensureHttps } from '@/utils/url';

import { EventCommentsCard } from './comments/EventCommentsCard';
import { EmailBlastButton } from './EmailBlastButton';
import { EventAdminActions } from './EventAdminActions';
import { Card } from './EventDetailCard';
import { EventFlagDialog } from './EventFlagDialog';
import { EventHostSection } from './EventHostSection';
import { eventMemberSectionFlags } from './eventMemberFlags';
import { GroupTextButton } from './GroupTextButton';
import { InvitedList } from './GuestChip';
import { InviteDialog } from './InviteDialog';
import { RsvpGuestList } from './RsvpGuestList';

interface Props {
  event: Event;
  token?: string;
}

export function EventMemberSection({ event, token }: Props) {
  const user = useAuthStore((s) => s.user);
  if (!user && !token) return null;

  const { isHostOrEventManager, canEdit, canInvite, showRsvp, showStandaloneInvited } =
    eventMemberSectionFlags(event, user);

  return (
    <div className="mt-8 flex flex-col gap-6">
      {user ? (
        <EventHostSection
          event={event}
          isHostOrEventManager={isHostOrEventManager}
          canEdit={canEdit}
          viewerId={user.id}
        />
      ) : null}
      <LocationSection event={event} />
      <LinksSection event={event} />
      <CostSection event={event} />
      {showRsvp ? (
        <Card label="who's going">
          <CapacityNote event={event} />
          <RsvpGuestList event={event} canSeeInvited={isHostOrEventManager} />
          {canInvite || isHostOrEventManager ? (
            <div className="mt-4 flex flex-col items-stretch gap-2">
              {canInvite ? <InviteSection event={event} /> : null}
              {isHostOrEventManager ? (
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
      {event.rsvpEnabled ? (
        <EventCommentsCard eventId={event.id} {...(token ? { token } : {})} />
      ) : null}
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
    <p className="text-muted -mt-2 mb-3 text-xs">
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
        className="text-brand-700 hover:text-brand-900 text-sm [overflow-wrap:anywhere] break-words"
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
              className="text-brand-700 hover:text-brand-900 [overflow-wrap:anywhere] break-words"
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
  const paymentPrefillOn = useFlag(Feature.EventPaymentConfirmation);
  const items: { label: string; url?: string }[] = [];
  if (event.price) items.push({ label: formatPrice(event.price) });
  if (event.venmoLink) items.push({ label: 'venmo', url: ensureHttps(event.venmoLink) });
  if (event.cashappLink) {
    const url = paymentPrefillOn
      ? toCashAppPayUrl(event.cashappLink, { price: event.price })
      : ensureHttps(event.cashappLink);
    items.push({ label: 'cashapp', url });
  }
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
                className="text-brand-700 hover:text-brand-900 [overflow-wrap:anywhere] break-words"
              >
                {item.label}
              </a>
            ) : (
              <span className="text-foreground [overflow-wrap:anywhere] break-words">
                {item.label}
              </span>
            )}
          </li>
        ))}
      </ul>
    </Card>
  );
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
