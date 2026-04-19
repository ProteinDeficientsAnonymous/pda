// The authed branch of the event detail. Renders the sections that the
// backend gates behind auth: hosts, location, links, cost, invite, rsvp,
// plus the admin actions card for the event's creator / co-hosts / managers.

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { RsvpSection } from './RsvpSection';
import { EventAdminActions } from './EventAdminActions';
import { EventFlagDialog } from './EventFlagDialog';
import { InviteDialog } from './InviteDialog';
import { hasPermission } from '@/models/permissions';
import { Permission } from '@/models/permissions';
import type { Event } from '@/models/event';
import { EventStatus, InvitePermission } from '@/models/event';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';

interface Props {
  event: Event;
}

export function EventMemberSection({ event }: Props) {
  const user = useAuthStore((s) => s.user);
  if (!user) return null;

  const isCoHost = user.id === event.createdById || event.coHostIds.includes(user.id);
  const canManageEvents = hasPermission(user, Permission.ManageEvents);
  const canSeeInvited = isCoHost || canManageEvents || event.invitedUserIds.includes(user.id);
  const canInvite = isCoHost || event.invitePermission === InvitePermission.AllMembers;
  const showRsvp = !event.isPast && event.rsvpEnabled && event.status !== EventStatus.Cancelled;

  return (
    <div className="mt-8 flex flex-col gap-6">
      <HostSection event={event} />
      <LocationSection event={event} />
      <LinksSection event={event} />
      <CostSection event={event} />
      {canInvite ? <InviteSection event={event} /> : null}
      {showRsvp ? (
        <Card label="rsvp">
          <RsvpSection event={event} canSeeInvited={canSeeInvited} />
        </Card>
      ) : null}
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

function Card({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4">
      <h2 className="mb-3 text-xs font-medium tracking-wide text-neutral-500 uppercase">{label}</h2>
      {children}
    </section>
  );
}

function HostSection({ event }: { event: Event }) {
  const hosts: { id: string; name: string; photoUrl: string }[] = [];
  if (event.createdById && event.createdByName) {
    hosts.push({
      id: event.createdById,
      name: event.createdByName,
      photoUrl: event.createdByPhotoUrl,
    });
  }
  event.coHostIds.forEach((id, i) => {
    hosts.push({
      id,
      name: event.coHostNames[i] ?? 'member',
      photoUrl: event.coHostPhotoUrls[i] ?? '',
    });
  });
  if (hosts.length === 0) return null;
  const label = hosts.length > 1 ? 'hosts' : 'host';
  return (
    <Card label={label}>
      <div className="flex flex-wrap gap-2">
        {hosts.map((h) => (
          <HostChip key={h.id} name={h.name} photoUrl={h.photoUrl} />
        ))}
      </div>
    </Card>
  );
}

function HostChip({ name, photoUrl }: { name: string; photoUrl: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full bg-neutral-100 px-2 py-1 text-sm">
      {photoUrl ? (
        <img src={photoUrl} alt="" className="h-6 w-6 rounded-full object-cover" loading="lazy" />
      ) : (
        <span
          aria-hidden="true"
          className="flex h-6 w-6 items-center justify-center rounded-full bg-neutral-300 text-xs text-neutral-700"
        >
          {name.slice(0, 1).toUpperCase()}
        </span>
      )}
      {name}
    </span>
  );
}

function LocationSection({ event }: { event: Event }) {
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
        className="text-sm text-neutral-900 hover:underline"
      >
        {primary}
      </a>
    </Card>
  );
}

function LinksSection({ event }: { event: Event }) {
  const links: { label: string; url: string }[] = [];
  if (event.whatsappLink) links.push({ label: 'whatsapp group', url: event.whatsappLink });
  if (event.partifulLink) links.push({ label: 'partiful', url: event.partifulLink });
  if (event.otherLink) links.push({ label: event.otherLink, url: event.otherLink });
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
              className="text-neutral-900 hover:underline"
            >
              {l.label}
            </a>
          </li>
        ))}
        {feedbackSurveys.map((slug) => (
          <li key={slug}>
            <Link to={`/surveys/${slug}`} className="text-neutral-900 hover:underline">
              give feedback
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function CostSection({ event }: { event: Event }) {
  const items: { label: string; value?: string; url?: string }[] = [];
  if (event.price) items.push({ label: event.price });
  if (event.venmoLink) items.push({ label: 'venmo', url: event.venmoLink });
  if (event.cashappLink) items.push({ label: 'cash app', url: event.cashappLink });
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
                className="text-neutral-900 hover:underline"
              >
                {item.label}
              </a>
            ) : (
              <span className="text-neutral-800">{item.label}</span>
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
    <Card label="invite">
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
    </Card>
  );
}
