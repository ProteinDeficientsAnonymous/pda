import { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

import { extractApiError } from '@/api/apiErrors';
import { useRemoveCohost, useRescindCohostInvite } from '@/api/cohostInvites';
import { useConfirm } from '@/components/ui/useConfirm';
import type { Event, PendingCohostInvite } from '@/models/event';

import { AddCoHostDialog } from './AddCoHostDialog';
import { Card } from './EventDetailCard';

interface HostRow {
  userId: string;
  name: string;
  photoUrl: string;
}

export function EventHostSection({
  event,
  canEdit,
  canInviteCohost,
  viewerId,
}: {
  event: Event;
  canEdit: boolean;
  canInviteCohost: boolean;
  viewerId: string | null;
}) {
  const [addOpen, setAddOpen] = useState(false);
  const { confirm, element: confirmElement } = useConfirm();
  const remove = useRemoveCohost();

  const hosts: HostRow[] = event.coHostIds.map((id, i) => ({
    userId: id,
    name: event.coHostNames[i] ?? 'member',
    photoUrl: event.coHostPhotoUrls[i] ?? '',
  }));
  // backend already scopes pending invites to creator/accepted co-hosts; others get []
  const pending = event.pendingCohostInvites;
  if (hosts.length === 0 && pending.length === 0 && !canEdit) return null;
  const totalChips = hosts.length + pending.length;
  const label = totalChips > 1 ? 'hosts' : 'host';

  async function removeCohost(host: HostRow) {
    const isSelf = host.userId === viewerId;
    if (isSelf) {
      const ok = await confirm({
        title: 'step down as host?',
        message: "you'll lose host access — someone else will need to add you back later.",
        confirmLabel: 'step down',
        destructive: true,
      });
      if (!ok) return;
    }
    remove.mutate(
      { eventId: event.id, userId: host.userId },
      {
        onError: (err) => {
          const fallback = isSelf
            ? "couldn't step down — try again"
            : "couldn't remove — try again";
          toast.error(extractApiError(err) ?? fallback);
        },
      },
    );
  }

  return (
    <Card label={label}>
      <div className="flex flex-wrap items-center gap-2">
        {hosts.map((h) => {
          const isSelf = h.userId === viewerId;
          const canRemove = (canEdit || isSelf) && !remove.isPending;
          return (
            <HostChip
              key={h.userId}
              host={h}
              canRemove={canRemove}
              onRemove={() => {
                void removeCohost(h);
              }}
              isSelf={isSelf}
            />
          );
        })}
        {pending.map((inv) => (
          <PendingHostChip key={inv.id} eventId={event.id} invite={inv} canRescind={canEdit} />
        ))}
        {canEdit ? (
          <span className="group relative inline-flex">
            <button
              type="button"
              onClick={() => {
                if (canInviteCohost) setAddOpen(true);
              }}
              disabled={!canInviteCohost}
              aria-label="add co-host"
              aria-describedby={canInviteCohost ? undefined : 'add-cohost-disabled-reason'}
              className="bg-surface-dim text-foreground-secondary hover:bg-surface-dim/70 disabled:hover:bg-surface-dim inline-flex h-8 w-8 items-center justify-center rounded-full pb-0.5 text-xl leading-none disabled:cursor-not-allowed disabled:opacity-50"
            >
              +
            </button>
            {!canInviteCohost ? (
              <span
                id="add-cohost-disabled-reason"
                role="tooltip"
                className="bg-foreground text-surface pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 -translate-x-1/2 rounded px-2 py-1 text-xs whitespace-nowrap opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100"
              >
                can't invite co-hosts to a past event
              </span>
            ) : null}
          </span>
        ) : null}
      </div>
      {canInviteCohost ? (
        <AddCoHostDialog
          event={event}
          open={addOpen}
          onClose={() => {
            setAddOpen(false);
          }}
        />
      ) : null}
      {confirmElement}
    </Card>
  );
}

function HostChip({
  host,
  canRemove,
  onRemove,
  isSelf,
}: {
  host: HostRow;
  canRemove: boolean;
  onRemove: () => void;
  isSelf: boolean;
}) {
  return (
    <span className="bg-surface-dim hover:bg-surface-dim/70 inline-flex items-center gap-2 rounded-full px-2 py-1 text-sm">
      <Link to={`/members/${host.userId}`} className="inline-flex items-center gap-2">
        {host.photoUrl ? (
          <img
            src={host.photoUrl}
            alt=""
            className="h-6 w-6 rounded-full object-cover"
            loading="lazy"
          />
        ) : (
          <span
            aria-hidden="true"
            className="bg-toggle-off text-foreground-secondary flex h-6 w-6 items-center justify-center rounded-full text-xs"
          >
            {host.name.slice(0, 1).toLowerCase()}
          </span>
        )}
        {host.name}
      </Link>
      {canRemove ? (
        <button
          type="button"
          aria-label={isSelf ? 'step down as host' : `remove ${host.name} as co-host`}
          onClick={onRemove}
          className="text-muted hover:text-foreground ms-1"
        >
          ×
        </button>
      ) : null}
    </span>
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
