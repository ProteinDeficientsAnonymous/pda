// The authed branch of the event detail. Renders the sections that the
// backend gates behind auth: hosts, location, links, cost, invite, rsvp,
// plus the admin actions card for the event's creator / co-hosts / managers.

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { useRescindCohostInvite } from '@/api/cohostInvites';
import { RsvpSection } from './RsvpSection';
import { InvitedList } from './RsvpGuestList';
import { EventAdminActions } from './EventAdminActions';
import { EventAttendancePanel } from './EventAttendancePanel';
import { EventFlagDialog } from './EventFlagDialog';
import { InviteDialog } from './InviteDialog';
import { AddCoHostDialog } from './AddCoHostDialog';
import { hasPermission } from '@/models/permissions';
import { Permission } from '@/models/permissions';
import type { Event, PendingCohostInvite } from '@/models/event';
import { EventStatus, InvitePermission } from '@/models/event';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { ensureHttps } from '@/utils/url';

interface Props {
  event: Event;
}

export function EventMemberSection({ event }: Props) {
  const user = useAuthStore((s) => s.user);
  if (!user) return null;

  const isCoHost = user.id === event.createdById || event.coHostIds.includes(user.id);
  const canManageEvents = hasPermission(user, Permission.ManageEvents);
  const canSeeInvited = isCoHost || canManageEvents;
  const isCancelled = event.status === EventStatus.Cancelled;
  const canInvite =
    !isCancelled && (isCoHost || event.invitePermission === InvitePermission.AllMembers);
  const showRsvp = !event.isPast && event.rsvpEnabled && event.status !== EventStatus.Cancelled;
  const showStandaloneInvited = !showRsvp && canSeeInvited && event.invitedCount > 0;

  return (
    <div className="mt-8 flex flex-col gap-6">
      <HostSection event={event} canEdit={isCoHost && !isCancelled} />
      <LocationSection event={event} />
      <LinksSection event={event} />
      <CostSection event={event} />
      {showRsvp ? (
        <Card label="rsvp">
          <RsvpSection event={event} canSeeInvited={canSeeInvited} />
        </Card>
      ) : null}
      {showStandaloneInvited ? (
        <Card label="invited">
          <InvitedList event={event} />
        </Card>
      ) : null}
      {canInvite ? <InviteSection event={event} /> : null}
      {canSeeInvited && event.rsvpEnabled ? <EventAttendancePanel event={event} /> : null}
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
    <section className="border-border bg-surface rounded-lg border p-4">
      <h2 className="text-muted mb-3 text-xs font-medium tracking-wide">{label}</h2>
      {children}
    </section>
  );
}

function HostSection({ event, canEdit }: { event: Event; canEdit: boolean }) {
  const [addOpen, setAddOpen] = useState(false);
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
  // Backend only includes pending invites for the creator + accepted co-hosts.
  // Other viewers always get an empty list, so the chips never leak.
  const pending = event.pendingCohostInvites;
  if (hosts.length === 0 && pending.length === 0 && !canEdit) return null;
  const totalChips = hosts.length + pending.length;
  const label = totalChips > 1 ? 'hosts' : 'host';
  return (
    <Card label={label}>
      <div className="flex flex-wrap items-center gap-2">
        {hosts.map((h) => (
          <HostChip key={h.id} id={h.id} name={h.name} photoUrl={h.photoUrl} />
        ))}
        {pending.map((inv) => (
          <PendingHostChip key={inv.id} eventId={event.id} invite={inv} canRescind={canEdit} />
        ))}
        {canEdit ? (
          <button
            type="button"
            onClick={() => {
              setAddOpen(true);
            }}
            aria-label="add co-host"
            className="bg-surface-dim text-foreground-secondary hover:bg-surface-dim/70 inline-flex h-8 w-8 items-center justify-center rounded-full text-lg"
          >
            +
          </button>
        ) : null}
      </div>
      {canEdit ? (
        <AddCoHostDialog
          event={event}
          open={addOpen}
          onClose={() => {
            setAddOpen(false);
          }}
        />
      ) : null}
    </Card>
  );
}

function HostChip({ id, name, photoUrl }: { id: string; name: string; photoUrl: string }) {
  return (
    <Link
      to={`/members/${id}`}
      className="bg-surface-dim hover:bg-surface-dim/70 inline-flex items-center gap-2 rounded-full px-2 py-1 text-sm"
    >
      {photoUrl ? (
        <img src={photoUrl} alt="" className="h-6 w-6 rounded-full object-cover" loading="lazy" />
      ) : (
        <span
          aria-hidden="true"
          className="bg-toggle-off text-foreground-secondary flex h-6 w-6 items-center justify-center rounded-full text-xs"
        >
          {name.slice(0, 1).toLowerCase()}
        </span>
      )}
      {name}
    </Link>
  );
}

function PendingHostChip({
  eventId,
  invite,
  canRescind,
}: {
  eventId: string;
  invite: PendingCohostInvite;
  canRescind: boolean;
}) {
  const rescind = useRescindCohostInvite();
  const tooltip = `invited ${formatRelativeDays(invite.invitedAt)} — hasn't responded yet`;
  return (
    <span
      className="bg-surface-dim/60 text-foreground-secondary inline-flex items-center gap-2 rounded-full px-2 py-1 text-sm opacity-60 grayscale"
      title={tooltip}
      aria-label={`${invite.userName} (pending)`}
    >
      {invite.userPhotoUrl ? (
        <img
          src={invite.userPhotoUrl}
          alt=""
          className="h-6 w-6 rounded-full object-cover"
          loading="lazy"
        />
      ) : (
        <span
          aria-hidden="true"
          className="bg-toggle-off text-foreground-secondary flex h-6 w-6 items-center justify-center rounded-full text-xs"
        >
          {invite.userName.slice(0, 1).toLowerCase()}
        </span>
      )}
      {invite.userName}
      <span className="bg-surface-dim text-muted rounded-full px-1.5 py-0.5 text-[10px] uppercase">
        pending
      </span>
      {canRescind ? (
        <button
          type="button"
          aria-label={`rescind invite to ${invite.userName}`}
          disabled={rescind.isPending}
          onClick={() => {
            rescind.mutate(
              { eventId, inviteId: invite.id },
              { onError: () => toast.error("couldn't rescind — try again") },
            );
          }}
          className="text-muted hover:text-foreground ms-1 disabled:opacity-50"
        >
          ×
        </button>
      ) : null}
    </span>
  );
}

// Returns "today", "yesterday", or "N days ago" for the host-row pending tooltip.
function formatRelativeDays(date: Date): string {
  const ms = Date.now() - date.getTime();
  const days = Math.floor(ms / (1000 * 60 * 60 * 24));
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  return `${String(days)} days ago`;
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

// Strip scheme + optional www. and trailing slash for display. `href` should
// still get the full URL (via ensureHttps).
function prettyUrl(url: string): string {
  return url
    .replace(/^https?:\/\//i, '')
    .replace(/^www\./i, '')
    .replace(/\/$/, '');
}
