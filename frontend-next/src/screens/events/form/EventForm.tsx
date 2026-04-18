// Event create/edit form. Composes the section files. On create the photo
// upload is chained after the POST (the backend photo endpoint is scoped by
// :id, so an event must exist first).

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { MemberSearchResult } from '@/api/userSearch';
import {
  emptyEventFormValues,
  eventToFormValues,
  extractEventError,
  useCreateEvent,
  useUpdateEvent,
  useUploadEventPhoto,
  useDeleteEventPhoto,
  type EventFormValues,
} from '@/api/eventWrites';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { MemberPicker } from '@/components/MemberPicker';
import type { Event } from '@/models/event';
import { Permission, hasPermission } from '@/models/permissions';
import { EventFormBasics } from './EventFormBasics';
import { EventFormLinksAndCost } from './EventFormLinksAndCost';
import { EventFormRsvp } from './EventFormRsvp';
import { EventFormPhoto } from './EventFormPhoto';
import { validateEventForm } from './validateEventForm';

interface Props {
  existing?: Event;
}

export function EventForm({ existing }: Props) {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const canTagOfficial = hasPermission(user, Permission.TagOfficialEvent);

  const [values, setValues] = useState<EventFormValues>(() =>
    existing ? eventToFormValues(existing) : emptyEventFormValues(),
  );
  const [coHosts, setCoHosts] = useState<MemberSearchResult[]>([]);
  const [invited, setInvited] = useState<MemberSearchResult[]>([]);
  const [errors, setErrors] = useState<Partial<Record<keyof EventFormValues, string>>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [pendingPhoto, setPendingPhoto] = useState<Blob | null>(null);

  const create = useCreateEvent();
  const update = useUpdateEvent(existing?.id ?? '');
  const uploadPhoto = useUploadEventPhoto(existing?.id ?? '');
  const deletePhoto = useDeleteEventPhoto(existing?.id ?? '');

  const saving = create.isPending || update.isPending || uploadPhoto.isPending;
  const isDraft = values.status === 'draft';

  function patch(p: Partial<EventFormValues>) {
    setValues((v) => ({ ...v, ...p }));
  }

  async function submit(nextStatus: 'active' | 'draft') {
    setServerError(null);
    const merged: EventFormValues = {
      ...values,
      coHostIds: coHosts.map((m) => m.id),
      invitedUserIds: invited.map((m) => m.id),
      status: nextStatus,
    };
    const errs = validateEventForm(merged);
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      return;
    }
    setErrors({});
    try {
      if (existing) {
        await update.mutateAsync(merged);
      } else {
        const created = await create.mutateAsync(merged);
        if (pendingPhoto) {
          try {
            await uploadPhoto.mutateAsync(pendingPhoto);
          } catch {
            // Event was saved; only the photo failed. Let the user retry from
            // the edit screen rather than blocking the whole save.
          }
        }
        void navigate(`/events/${created.id}`);
        return;
      }
      void navigate(`/events/${existing.id}`);
    } catch (err) {
      setServerError(extractEventError(err));
    }
  }

  async function onCropPhoto(blob: Blob) {
    if (existing) {
      await uploadPhoto.mutateAsync(blob);
    } else {
      // Stash until the event is created.
      setPendingPhoto(blob);
    }
  }

  async function onDeletePhoto() {
    if (!existing) {
      setPendingPhoto(null);
      return;
    }
    await deletePhoto.mutateAsync();
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void submit('active');
      }}
      className="flex flex-col gap-8"
    >
      <EventFormBasics
        values={values}
        onChange={patch}
        errors={errors}
        canTagOfficial={canTagOfficial}
      />

      <EventFormPhoto
        photoUrl={existing?.photoUrl ?? (pendingPhoto ? 'pending' : '')}
        photoUpdatedAt={null}
        onCrop={onCropPhoto}
        onDelete={existing || pendingPhoto ? onDeletePhoto : undefined}
        disabled={saving}
      />

      <EventFormRsvp values={values} onChange={patch} />
      <EventFormLinksAndCost values={values} onChange={patch} errors={errors} />

      <section className="flex flex-col gap-4">
        <h2 className="text-xs font-medium tracking-wide text-neutral-500 uppercase">hosts</h2>
        <MemberPicker
          label="co-hosts"
          selected={coHosts}
          onChange={setCoHosts}
          excludeIds={user ? [user.id] : []}
          hint="co-hosts can edit the event and manage rsvps"
        />
        {values.visibility === 'invite_only' ? (
          <MemberPicker
            label="invited members"
            selected={invited}
            onChange={setInvited}
            excludeIds={user ? [user.id, ...coHosts.map((m) => m.id)] : coHosts.map((m) => m.id)}
          />
        ) : null}
      </section>

      {serverError ? (
        <p role="alert" className="text-sm text-red-600">
          {serverError}
        </p>
      ) : null}

      <div className="flex flex-wrap justify-end gap-2">
        {!existing || isDraft ? (
          <Button
            variant="secondary"
            onClick={() => void submit('draft')}
            disabled={saving}
            type="button"
          >
            save draft
          </Button>
        ) : null}
        <Button type="submit" disabled={saving}>
          {saving ? 'saving…' : existing ? 'save' : 'publish'}
        </Button>
      </div>
    </form>
  );
}
