// Admin actions for events: edit, publish (drafts), cancel, delete.
// Visible only to the creator, a co-host, or a user with manage_events.

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { extractApiErrorOr } from '@/api/apiErrors';
import { useCancelEvent, useDeleteEvent, useUpdateEvent } from '@/api/eventWrites';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import type { Event } from '@/models/event';
import { EventStatus } from '@/models/event';
import { Permission, hasPermission } from '@/models/permissions';

interface Props {
  event: Event;
}

export function EventAdminActions({ event }: Props) {
  const user = useAuthStore((s) => s.user);
  if (!user) return null;

  const isCreator = user.id === event.createdById;
  const isCoHost = event.coHostIds.includes(user.id);
  const canManage = hasPermission(user, Permission.ManageEvents);
  const canEdit = isCreator || isCoHost || canManage;
  if (!canEdit) return null;

  return (
    <section className="border-border bg-surface flex flex-col gap-2 rounded-lg border p-4">
      <h2 className="text-muted mb-1 text-xs font-medium tracking-wide">event actions</h2>
      <AdminActionRow event={event} isCreator={isCreator} canManage={canManage} />
    </section>
  );
}

function AdminActionRow({
  event,
  isCreator,
  canManage,
}: {
  event: Event;
  isCreator: boolean;
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
  const canDelete = (isCreator || canManage) && (isDraft || isCancelled || hasNoAttendees);
  const showCancel = !isCancelled && !isDraft && !hasNoAttendees;
  // Drafts are always editable — the edit-window cutoff protects the
  // historical record of published events, which drafts don't have.
  const canEditEvent = isDraft || isEditWindowOpen(event);

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
      <div className="flex flex-wrap gap-2">
        {canEditEvent ? (
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
            className="border-red-300 text-red-700 hover:bg-red-50"
          >
            delete
          </Button>
        ) : null}
      </div>
      {publishError ? (
        <p role="alert" className="text-sm text-red-600">
          {publishError}
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
          <p role="alert" className="mt-3 text-sm text-red-600">
            {cancelError}
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
          <p role="alert" className="mt-3 text-sm text-red-600">
            {deleteError}
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

// Editing stays open until 6 hours after the event's end (or start, if no end
// set) — gives hosts room to fix typos, post follow-ups, or tweak details
// during and right after the event without hitting a stale-data wall.
const EDIT_GRACE_MS = 6 * 60 * 60 * 1000;

function isEditWindowOpen(event: Event): boolean {
  const reference = event.endDatetime ?? event.startDatetime;
  if (!reference) return true;
  return Date.now() <= reference.getTime() + EDIT_GRACE_MS;
}

function extractMutationError(err: unknown): string {
  return extractApiErrorOr(err, "couldn't update the event — try again");
}
