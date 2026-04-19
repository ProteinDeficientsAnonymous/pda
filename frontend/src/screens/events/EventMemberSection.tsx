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
  const isCancelled = event.status === EventStatus.Cancelled;
  const canInvite =
    !isCancelled && (isCoHost || event.invitePermission === InvitePermission.AllMembers);
  const showRsvp = !event.isPast && event.rsvpEnabled && event.status !== EventStatus.Cancelled;

  return (
    <div className="mt-8 flex flex-col gap-6">
      <HostSection event={event} />
      <LocationSection event={event} />
      <LinksSection event={event} />
      <CostSection event={event} />
      {showRsvp ? (
        <Card label="rsvp">
          <RsvpSection event={event} canSeeInvited={canSeeInvited} />
        </Card>
      ) : null}
      {canInvite ? <InviteSection event={event} /> : null}
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
    <section className="rounded-lg border border-border bg-surface p-4">
      <h2 className="mb-3 text-xs font-medium tracking-wide text-muted">{label}</h2>
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
          <HostChip key={h.id} id={h.id} name={h.name} photoUrl={h.photoUrl} />
        ))}
      </div>
    </Card>
  );
}

function HostChip({ id, name, photoUrl }: { id: string; name: string; photoUrl: string }) {
  return (
    <Link
      to={`/members/${id}`}
      className="inline-flex items-center gap-2 rounded-full bg-surface-dim px-2 py-1 text-sm hover:bg-surface-dim/70"
    >
      {photoUrl ? (
        <img src={photoUrl} alt="" className="h-6 w-6 rounded-full object-cover" loading="lazy" />
      ) : (
        <span
          aria-hidden="true"
          className="flex h-6 w-6 items-center justify-center rounded-full bg-toggle-off text-xs text-foreground-secondary"
        >
          {name.slice(0, 1).toUpperCase()}
        </span>
      )}
      {name}
    </Link>
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
        className="text-brand-700 hover:text-brand-900 text-sm"
      >
        {primary}
      </a>
    </Card>
  );
}

function LinksSection({ event }: { event: Event }) {
  const links: { label: string; url: string }[] = [];
  if (event.whatsappLink) {
    links.push({ label: 'whatsapp group', url: ensureHttps(event.whatsappLink) });
  }
  if (event.partifulLink) links.push({ label: 'partiful', url: ensureHttps(event.partifulLink) });
  if (event.otherLink) {
    links.push({ label: prettyUrl(event.otherLink), url: ensureHttps(event.otherLink) });
  }
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

function CostSection({ event }: { event: Event }) {
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

function ensureHttps(url: string): string {
  return /^https?:\/\//i.test(url) ? url : `https://${url}`;
}

// Strip scheme + optional www. and trailing slash for display. `href` should
// still get the full URL (via ensureHttps).
function prettyUrl(url: string): string {
  return url
    .replace(/^https?:\/\//i, '')
    .replace(/^www\./i, '')
    .replace(/\/$/, '');
}
