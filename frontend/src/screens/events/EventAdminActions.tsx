// Admin actions for events: edit, duplicate, cancel, archive. Visible only
// to the creator, a co-host, or a user with manage_events. Matches
// EventAdminActions from the flutter app.

import { isAxiosError } from 'axios';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useArchiveEvent, useUpdateEvent } from '@/api/eventWrites';
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
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [archiveError, setArchiveError] = useState<string | null>(null);

  const update = useUpdateEvent(event.id);
  const archive = useArchiveEvent(event.id);
  const [publishError, setPublishError] = useState<string | null>(null);

  const isCancelled = event.status === EventStatus.Cancelled;
  const isDraft = event.status === EventStatus.Draft;
  const hasNoAttendees = event.attendingCount === 0;
  const canArchive = (isCreator || canManage) && (isDraft || isCancelled || hasNoAttendees);
  const showCancel = !isCancelled && !isDraft && !hasNoAttendees;
  const canEditEvent = !event.isPast;

  async function onCancel() {
    setCancelError(null);
    try {
      await archive.mutateAsync();
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

  async function onArchive() {
    setArchiveError(null);
    try {
      await archive.mutateAsync();
      void navigate('/calendar', { replace: true });
    } catch (err) {
      setArchiveError(extractMutationError(err));
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
        {canArchive ? (
          <Button
            variant="secondary"
            onClick={() => {
              setArchiveOpen(true);
            }}
            className="border-red-300 text-red-700 hover:bg-red-50"
          >
            archive
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
          — you can't un-cancel from the React app yet.
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
            disabled={archive.isPending}
          >
            {archive.isPending ? 'cancelling…' : 'cancel event'}
          </Button>
        </div>
      </Dialog>

      <Dialog
        open={archiveOpen}
        onClose={() => {
          setArchiveOpen(false);
          setArchiveError(null);
        }}
        title="archive event"
      >
        <p className="text-foreground-secondary text-sm">
          archive this event? it will be marked cancelled and hidden from the active calendar. This
          cannot be undone from the React app yet.
        </p>
        {archiveError ? (
          <p role="alert" className="mt-3 text-sm text-red-600">
            {archiveError}
          </p>
        ) : null}
        <div className="mt-4 flex justify-end gap-2">
          <Button
            variant="ghost"
            onClick={() => {
              setArchiveOpen(false);
              setArchiveError(null);
            }}
            disabled={archive.isPending}
          >
            back
          </Button>
          <Button
            onClick={() => {
              void onArchive();
            }}
            disabled={archive.isPending}
          >
            {archive.isPending ? 'archiving…' : 'archive'}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}

function extractMutationError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail.toLowerCase();
  }
  if (err instanceof Error && err.message) return err.message.toLowerCase();
  return "couldn't update the event — try again";
}
