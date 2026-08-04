import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useCancelEvent, useDeleteEvent, useUpdateEvent } from '@/api/eventWrites';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import type { Event } from '@/models/event';
import { EventStatus } from '@/models/event';
import { hasPermission, Permission } from '@/models/permissions';

import { isEventEditable } from './eventEditGate';

interface Props {
  event: Event;
}

export function EventAdminActions({ event }: Props) {
  const user = useAuthStore((s) => s.user);
  if (!user) return null;

  // co_hosts is the sole source of truth for hosts; created_by is a permanent
  // audit field that outlives a step-down.
  const isCoHost = event.coHostIds.includes(user.id);
  const canManage = hasPermission(user, Permission.ManageEvents);
  if (!isCoHost && !canManage) return null;

  return <AdminActionRow event={event} isHost={isCoHost} canManage={canManage} />;
}

function AdminActionRow({
  event,
  isHost,
  canManage,
}: {
  event: Event;
  isHost: boolean;
  canManage: boolean;
}) {
  const navigate = useNavigate();
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const update = useUpdateEvent(event.id);
  const cancelMut = useCancelEvent(event.id);
  const deleteMut = useDeleteEvent(event.id);
  const [publishError, setPublishError] = useState<string | null>(null);

  const isCancelled = event.status === EventStatus.Cancelled;
  const isDraft = event.status === EventStatus.Draft;
  const hasNoAttendees = event.attendingCount === 0;
  const canDelete = (isHost || canManage) && (isDraft || isCancelled || hasNoAttendees);
  const showCancel = !isCancelled && !isDraft && !hasNoAttendees && !event.isPast;
  const eventIsEditable = isEventEditable(event);

  async function onCancel() {
    setCancelError(null);
    try {
      await cancelMut.mutateAsync();
      setCancelOpen(false);
    } catch (err) {
      setCancelError(extractMutationError(err));
    }
  }

  async function onPublish() {
    setPublishError(null);
    try {
      await update.mutateAsync({ status: 'active' });
    } catch (err) {
      setPublishError(extractMutationError(err));
    }
  }

  async function onDelete() {
    setDeleteError(null);
    try {
      await deleteMut.mutateAsync();
      void navigate('/calendar', { replace: true });
    } catch (err) {
      setDeleteError(extractMutationError(err));
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap justify-center gap-2">
        {eventIsEditable ? (
          <Button variant="secondary" onClick={() => void navigate(`/events/${event.id}/edit`)}>
            edit
          </Button>
        ) : null}
        {isDraft ? (
          <Button
            onClick={() => {
              void onPublish();
            }}
            disabled={update.isPending}
          >
            {update.isPending ? 'publishing…' : 'publish'}
          </Button>
        ) : null}
        {showCancel ? (
          <Button
            variant="secondary"
            onClick={() => {
              setCancelOpen(true);
            }}
          >
            cancel event
          </Button>
        ) : null}
        {canDelete ? (
          <Button
            variant="secondary"
            onClick={() => {
              setDeleteOpen(true);
            }}
            className="border-destructive-border text-destructive hover:bg-destructive-subtle font-medium"
          >
            delete
          </Button>
        ) : null}
      </div>
      {!eventIsEditable && !isCancelled ? (
        <p className="text-foreground-tertiary text-center text-xs">
          editing closes 6 hours after the event ends
        </p>
      ) : null}
      {publishError ? (
        <p role="alert" className="text-sm font-medium text-red-600">
          ⚠ {publishError}
        </p>
      ) : null}

      <Dialog
        open={cancelOpen}
        onClose={() => {
          setCancelOpen(false);
          setCancelError(null);
        }}
        title="cancel event"
      >
        <p className="text-foreground-secondary text-sm">
          mark this event as cancelled? attendees will get a notification and see a cancelled badge
          — you can't un-cancel from the react app yet.
        </p>
        {cancelError ? (
          <p role="alert" className="mt-3 text-sm font-medium text-red-600">
            ⚠ {cancelError}
          </p>
        ) : null}
        <div className="mt-4 flex justify-end gap-2">
          <Button
            variant="ghost"
            onClick={() => {
              setCancelOpen(false);
              setCancelError(null);
            }}
          >
            back
          </Button>
          <Button
            onClick={() => {
              void onCancel();
            }}
            disabled={cancelMut.isPending}
          >
            {cancelMut.isPending ? 'cancelling…' : 'cancel event'}
          </Button>
        </div>
      </Dialog>

      <Dialog
        open={deleteOpen}
        onClose={() => {
          setDeleteOpen(false);
          setDeleteError(null);
        }}
        title="delete event"
      >
        <p className="text-foreground-secondary text-sm">
          delete this event? it will be removed from the calendar and can't be recovered from the
          react app.
        </p>
        {deleteError ? (
          <p role="alert" className="mt-3 text-sm font-medium text-red-600">
            ⚠ {deleteError}
          </p>
        ) : null}
        <div className="mt-4 flex justify-end gap-2">
          <Button
            variant="ghost"
            onClick={() => {
              setDeleteOpen(false);
              setDeleteError(null);
            }}
            disabled={deleteMut.isPending}
          >
            back
          </Button>
          <Button
            onClick={() => {
              void onDelete();
            }}
            disabled={deleteMut.isPending}
          >
            {deleteMut.isPending ? 'deleting…' : 'delete'}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}

function extractMutationError(err: unknown): string {
  return extractApiErrorOr(err, "couldn't update the event — try again");
}
