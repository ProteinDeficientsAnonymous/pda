// Admin actions for events: edit, duplicate, cancel, delete. Visible only
// to the creator, a co-host, or a user with manage_events. Matches
// EventAdminActions from the flutter app.

import { isAxiosError, type AxiosError } from 'axios';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { eventKeys } from '@/api/events';
import { useUpdateEvent } from '@/api/eventWrites';
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
    <section className="flex flex-col gap-2 rounded-lg border border-border bg-surface p-4">
      <h2 className="mb-1 text-xs font-medium tracking-wide text-muted">event actions</h2>
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
  const del = useDeleteEvent(event.id);
  const [publishError, setPublishError] = useState<string | null>(null);

  const isCancelled = event.status === EventStatus.Cancelled;
  const isDraft = event.status === EventStatus.Draft;
  const canDelete = (isCreator || canManage) && (isDraft || isCancelled);

  async function onCancel() {
    setCancelError(null);
    try {
      await update.mutateAsync({ status: 'cancelled' });
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
      await del.mutateAsync();
      void navigate('/calendar', { replace: true });
    } catch (err) {
      setDeleteError(extractMutationError(err));
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => void navigate(`/events/${event.id}/edit`)}>
          edit
        </Button>
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
        {!isCancelled && !isDraft ? (
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
        <p className="text-sm text-foreground-secondary">
          mark this event as cancelled? attendees will see a cancelled badge — you can't un-cancel
          from the React app yet.
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
            disabled={update.isPending}
          >
            {update.isPending ? 'cancelling…' : 'cancel event'}
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
        <p className="text-sm text-foreground-secondary">
          this permanently deletes the event and all rsvps. This cannot be undone.
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
            disabled={del.isPending}
          >
            back
          </Button>
          <Button
            onClick={() => {
              void onDelete();
            }}
            disabled={del.isPending}
          >
            {del.isPending ? 'deleting…' : 'delete'}
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

function useDeleteEvent(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async () => {
      try {
        await apiClient.delete(`/api/community/events/${eventId}/`);
      } catch (err) {
        if (isAxiosError(err)) throw new Error(extractDetail(err) ?? 'delete failed');
        throw err;
      }
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: eventKeys.list(isAuthed) });
    },
  });
}

function extractDetail(err: AxiosError): string | null {
  const d = (err.response?.data as { detail?: string } | undefined)?.detail;
  return d ?? null;
}
