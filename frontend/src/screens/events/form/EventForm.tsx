// Event create/edit form.
//
// Layout: hero photo → always-visible (title/when/where) → collapsible
// sections (hosts, details, rsvp, links, money) → actions.
//
// Photo-first by design: the Flutter app's form opened with a big cover
// banner so the flow feels inviting even before a title is typed. Sections
// collapse by default so simple events don't feel like a chore — summary
// badges on each header show what's already filled in.

import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { apiClient } from '@/api/client';
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
import { CollapsibleCard } from '@/components/ui/CollapsibleCard';
import { MemberPicker } from '@/components/MemberPicker';
import type { Event } from '@/models/event';
import { Permission, hasPermission } from '@/models/permissions';
import { EventFormBasics } from './EventFormBasics';
import { EventFormDetails } from './EventFormDetails';
import { EventFormLinks, EventFormMoney } from './EventFormLinksAndCost';
import { EventFormPhoto } from './EventFormPhoto';
import { EventFormRsvp } from './EventFormRsvp';
import { validateEventForm } from './validateEventForm';

interface Props {
  existing?: Event;
}

// Field → section map. Drives which CollapsibleCard opens on validation
// errors — keeping it in one place makes it easy to audit which fields
// surface where.
const DETAILS_FIELDS: readonly (keyof EventFormValues)[] = [
  'description',
  'visibility',
  'visibilityChoice',
  'eventType',
  'invitePermission',
];
const RSVP_FIELDS: readonly (keyof EventFormValues)[] = [
  'rsvpEnabled',
  'allowPlusOnes',
  'maxAttendees',
];
const LINK_FIELDS: readonly (keyof EventFormValues)[] = [
  'whatsappLink',
  'partifulLink',
  'otherLink',
];

function countFilled(values: EventFormValues, fields: readonly (keyof EventFormValues)[]) {
  return fields.filter((k) => {
    const v = values[k];
    return typeof v === 'string' && v.trim().length > 0;
  }).length;
}

function hasAnyError(
  errors: Partial<Record<keyof EventFormValues, string>>,
  fields: readonly (keyof EventFormValues)[],
) {
  return fields.some((k) => errors[k]);
}

export function EventForm({ existing }: Props) {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const canTagOfficial = hasPermission(user, Permission.TagOfficialEvent);
  const formRef = useRef<HTMLFormElement | null>(null);

  const [values, setValues] = useState<EventFormValues>(() =>
    existing ? eventToFormValues(existing) : emptyEventFormValues(),
  );
  const [coHosts, setCoHosts] = useState<MemberSearchResult[]>([]);
  const [invited, setInvited] = useState<MemberSearchResult[]>([]);
  // On edit, pre-run validation so issues in the loaded values (e.g. a stale
  // draft whose start is now in the past) are visible immediately instead of
  // waiting for the first save attempt.
  const [errors, setErrors] = useState<Partial<Record<keyof EventFormValues, string>>>(() =>
    existing ? validateEventForm(eventToFormValues(existing)) : {},
  );
  const [serverError, setServerError] = useState<string | null>(null);
  const [pendingPhoto, setPendingPhoto] = useState<Blob | null>(null);
  const pendingPhotoUrl = useMemo(
    () => (pendingPhoto ? URL.createObjectURL(pendingPhoto) : null),
    [pendingPhoto],
  );
  useEffect(() => {
    if (!pendingPhotoUrl) return;
    return () => {
      URL.revokeObjectURL(pendingPhotoUrl);
    };
  }, [pendingPhotoUrl]);
  // Buffered poll options — create-flow only. On submit we fire create-event
  // then POST the poll. If the poll POST fails we still land on the new
  // event's detail page and the host can retry from there.
  const [bufferedPollOptions, setBufferedPollOptions] = useState<Date[] | null>(null);

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
    const timeLocked = !!existing?.hasPoll && !existing.startDatetime;
    const merged: EventFormValues = {
      ...values,
      coHostIds: coHosts.map((m) => m.id),
      invitedUserIds: invited.map((m) => m.id),
      status: nextStatus,
    };
    const errs = validateEventForm(merged);
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      // Let the sections open first (via forceOpen), then scroll to the
      // first invalid field.
      requestAnimationFrame(() => {
        const firstInvalid = formRef.current?.querySelector<HTMLElement>('[aria-invalid="true"]');
        firstInvalid?.scrollIntoView({ block: 'center', behavior: 'smooth' });
        firstInvalid?.focus();
      });
      return;
    }
    setErrors({});
    try {
      if (existing) {
        // While a poll is active, the poll owns the time. Send a Partial
        // that omits start/end/tbd so useUpdateEvent's undefined-filter drops
        // them from the PATCH body (backend rejects those edits).
        const patchBody: Partial<EventFormValues> = timeLocked
          ? (() => {
              const { startDatetime: _s, endDatetime: _e, datetimeTbd: _t, ...rest } = merged;
              return rest;
            })()
          : merged;
        await update.mutateAsync(patchBody);
        if (nextStatus === 'draft') toast.success('saved draft');
        void navigate(`/events/${existing.id}`);
        return;
      }
      const created = await create.mutateAsync(merged);
      if (pendingPhoto) {
        try {
          await uploadPhoto.mutateAsync(pendingPhoto);
        } catch {
          // Event saved; only the photo failed. Let the user retry from edit.
        }
      }
      if (bufferedPollOptions && bufferedPollOptions.length >= 2) {
        try {
          await apiClient.post(`/api/community/events/${created.id}/poll/`, {
            options: bufferedPollOptions.map((d) => d.toISOString()),
          });
        } catch {
          toast.error("event saved, but couldn't create the poll — try from the event page");
        }
      }
      if (nextStatus === 'draft') toast.success('saved draft');
      void navigate(`/events/${created.id}`);
    } catch (err) {
      setServerError(extractEventError(err));
    }
  }

  async function onCropPhoto(blob: Blob) {
    if (existing) {
      await uploadPhoto.mutateAsync(blob);
    } else {
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

  // Summary helpers — small labels shown on collapsed section headers so the
  // user sees what's already filled without expanding.
  const detailsFilled = values.description.trim().length > 0;
  const linkCount = countFilled(values, LINK_FIELDS);
  const moneyFilled =
    values.price.trim().length > 0 ||
    values.venmoLink.trim().length > 0 ||
    values.cashappLink.trim().length > 0 ||
    values.zelleInfo.trim().length > 0;
  const hostsCount = coHosts.length;

  return (
    <form
      ref={formRef}
      onSubmit={(e) => {
        e.preventDefault();
        void submit('active');
      }}
      className="flex flex-col gap-4"
    >
      <EventFormPhoto
        photoUrl={existing?.photoUrl ?? pendingPhotoUrl ?? ''}
        photoUpdatedAt={null}
        onCrop={onCropPhoto}
        onDelete={existing || pendingPhoto ? onDeletePhoto : undefined}
        disabled={saving}
      />

      <EventFormBasics
        values={values}
        onChange={patch}
        errors={errors}
        timeLocked={!!existing?.hasPoll && !existing.startDatetime}
        existingEventId={existing?.id}
        existingHasPoll={!!existing?.hasPoll}
        bufferedPollOptions={bufferedPollOptions}
        onBufferPoll={setBufferedPollOptions}
      />

      <CollapsibleCard
        title="hosts"
        summary={
          hostsCount > 0
            ? `${String(hostsCount)} ${hostsCount === 1 ? 'person' : 'people'}`
            : undefined
        }
      >
        <MemberPicker
          label="co-hosts"
          selected={coHosts}
          onChange={setCoHosts}
          excludeIds={user ? [user.id] : []}
          hint="co-hosts get an invite — once they accept, they can edit the event and manage rsvps"
        />
      </CollapsibleCard>

      <CollapsibleCard
        title="details"
        summary={detailsFilled ? 'filled in' : undefined}
        error={hasAnyError(errors, DETAILS_FIELDS) ? 'needs attention' : undefined}
        forceOpen={hasAnyError(errors, DETAILS_FIELDS)}
      >
        <EventFormDetails
          values={values}
          onChange={patch}
          errors={errors}
          canTagOfficial={canTagOfficial}
        />
        {values.visibility === 'invite_only' ? (
          <div className="mt-4">
            <MemberPicker
              label="invited members"
              selected={invited}
              onChange={setInvited}
              excludeIds={user ? [user.id, ...coHosts.map((m) => m.id)] : coHosts.map((m) => m.id)}
            />
          </div>
        ) : null}
      </CollapsibleCard>

      <CollapsibleCard
        title="rsvp"
        summary={values.rsvpEnabled ? 'enabled' : undefined}
        error={hasAnyError(errors, RSVP_FIELDS) ? 'needs attention' : undefined}
        forceOpen={hasAnyError(errors, RSVP_FIELDS)}
      >
        <EventFormRsvp values={values} onChange={patch} errors={errors} />
      </CollapsibleCard>

      <CollapsibleCard
        title="links"
        summary={
          linkCount > 0 ? `${String(linkCount)} link${linkCount === 1 ? '' : 's'}` : undefined
        }
        error={hasAnyError(errors, LINK_FIELDS) ? 'needs attention' : undefined}
        forceOpen={hasAnyError(errors, LINK_FIELDS)}
      >
        <EventFormLinks values={values} onChange={patch} errors={errors} />
      </CollapsibleCard>

      <CollapsibleCard title="money" summary={moneyFilled ? 'added' : undefined}>
        <EventFormMoney values={values} onChange={patch} errors={errors} />
      </CollapsibleCard>

      {serverError ? (
        <p
          role="alert"
          className="rounded-[var(--radius-md)] border border-red-200 bg-red-50 p-3 text-sm text-red-700"
        >
          {serverError}
        </p>
      ) : null}

      <div className="border-border bg-background/95 fixed inset-x-0 bottom-0 z-50 flex flex-row gap-2 border-t px-4 py-3 backdrop-blur sm:static sm:z-auto sm:mx-0 sm:justify-end sm:border-0 sm:bg-transparent sm:p-0 sm:pt-2 sm:backdrop-blur-none">
        {!existing || isDraft ? (
          <Button
            variant="secondary"
            onClick={() => void submit('draft')}
            disabled={saving}
            type="button"
            className="flex-1"
          >
            save draft
          </Button>
        ) : null}
        <Button type="submit" disabled={saving} className="flex-1">
          {saving ? 'saving…' : !existing || isDraft ? 'publish' : 'save'}
        </Button>
      </div>
    </form>
  );
}
