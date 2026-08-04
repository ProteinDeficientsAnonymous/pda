import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import { getErrorParams, hasErrorCode } from '@/api/apiErrors';
import { apiClient } from '@/api/client';
import {
  emptyEventFormValues,
  type EventFormValues,
  eventToFormValues,
  extractEventError,
  useCreateEvent,
  useUpdateEvent,
  useUploadEventPhoto,
} from '@/api/eventWrites';
import type { MemberSearchResult } from '@/api/userSearch';
import { Code } from '@/api/validationCodes';
import { useAuthStore } from '@/auth/store';
import { MemberPicker } from '@/components/MemberPicker';
import { Button } from '@/components/ui/Button';
import { CollapsibleCard } from '@/components/ui/CollapsibleCard';
import { useConfirm } from '@/components/ui/useConfirm';
import { type Event, eventPath, EventType } from '@/models/event';
import { hasPermission, Permission } from '@/models/permissions';

import { EventFormBasics } from './EventFormBasics';
import { EventFormDetails } from './EventFormDetails';
import { EventFormLinks, EventFormMoney } from './EventFormLinksAndCost';
import { EventFormPhoto } from './EventFormPhoto';
import { EventFormRsvp } from './EventFormRsvp';
import { EventFormTags } from './EventFormTags';
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
  const canTagClub = hasPermission(user, Permission.TagClubEvent);
  const formRef = useRef<HTMLFormElement | null>(null);

  const [values, setValues] = useState<EventFormValues>(() =>
    existing ? eventToFormValues(existing) : emptyEventFormValues(),
  );
  const [coHosts, setCoHosts] = useState<MemberSearchResult[]>(() => {
    if (!existing) return [];
    return existing.coHostIds.map((id, idx) => ({
      id,
      fullName: existing.coHostNames[idx] ?? '',
      phoneNumber: '',
    }));
  });
  // On edit, pre-run validation so issues in the loaded values (e.g. a stale
  // draft whose start is now in the past) are visible immediately instead of
  // waiting for the first save attempt.
  const [errors, setErrors] = useState<Partial<Record<keyof EventFormValues, string>>>(() =>
    existing
      ? validateEventForm(
          eventToFormValues(existing),
          existing.startDatetime ? existing.startDatetime.toISOString() : null,
        )
      : {},
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
  const uploadPhoto = useUploadEventPhoto();
  const { confirm, element: confirmElement } = useConfirm();

  const saving = create.isPending || update.isPending || uploadPhoto.isPending;
  const isDraft = values.status === 'draft';

  function patch(p: Partial<EventFormValues>) {
    setValues((v) => ({ ...v, ...p }));
  }

  async function submit(nextStatus: 'active' | 'draft') {
    setServerError(null);
    const timeLocked = !!existing?.hasPoll && !existing.startDatetime;
    const coHostIds = coHosts.map((m) => m.id);
    const merged: EventFormValues = {
      ...values,
      coHostIds,
      status: nextStatus,
    };
    const errs = validateEventForm(
      merged,
      existing?.startDatetime ? existing.startDatetime.toISOString() : undefined,
    );
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
        // On edit, omit coHostIds so the backend preserves existing invites/co-hosts.
        const patchBody: Partial<EventFormValues> = timeLocked
          ? (() => {
              const {
                startDatetime: _s,
                endDatetime: _e,
                datetimeTbd: _t,
                coHostIds: _c,
                ...rest
              } = merged;
              return rest;
            })()
          : (() => {
              const { coHostIds: _c, ...rest } = merged;
              return rest;
            })();
        try {
          await update.mutateAsync(patchBody);
        } catch (err) {
          if (!hasErrorCode(err, Code.Event.WouldRemoveNonMembers)) throw err;
          const count = getErrorParams(err, Code.Event.WouldRemoveNonMembers)?.count;
          const message =
            count === 1
              ? "1 non-member is rsvp'd or waitlisted on this event — turning this off will remove them and email them that they've been removed."
              : `${String(count)} non-members are rsvp'd or waitlisted on this event — turning this off will remove them and email them that they've been removed.`;
          const ok = await confirm({
            title: 'remove non-members?',
            message,
            confirmLabel: 'remove them',
            destructive: true,
          });
          if (!ok) return;
          await update.mutateAsync({ ...patchBody, force: true });
        }
        if (nextStatus === 'draft') toast.success('saved draft');
        void navigate(eventPath(existing));
        return;
      }
      const created = await create.mutateAsync(merged);
      if (pendingPhoto) {
        try {
          await uploadPhoto.mutateAsync({ eventId: created.id, blob: pendingPhoto });
        } catch {
          // Event saved; only the photo failed. Surface it so the host knows
          // to re-add it from edit instead of the photo silently vanishing.
          toast.error("event saved, but the photo didn't upload — add it again from edit");
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
      void navigate(eventPath(created));
    } catch (err) {
      setServerError(extractEventError(err));
    }
  }

  async function onCropPhoto(blob: Blob) {
    if (existing) {
      await uploadPhoto.mutateAsync({ eventId: existing.id, blob });
    } else {
      setPendingPhoto(blob);
    }
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
      className="flex flex-col gap-6 lg:flex-row lg:items-start lg:gap-4"
    >
      {/* Sticky at top-[89px] (= header 57px + py-8 32px) so it pins with no
          scroll-up drift. Height is 100vh minus twice that offset so the flex
          box centers the photo on the true viewport middle (89 + (100vh-178)/2
          = 50vh), not the middle of the space below the header. */}
      <div className="lg:sticky lg:top-[89px] lg:flex lg:h-[calc(100vh-178px)] lg:w-full lg:flex-1 lg:items-center lg:justify-center lg:self-start">
        <div className="mx-auto w-full max-w-md">
          <EventFormPhoto
            photoUrl={existing?.photoUrl ?? pendingPhotoUrl ?? ''}
            photoUpdatedAt={existing?.photoUpdatedAt ?? null}
            onCrop={onCropPhoto}
            disabled={saving}
          />
        </div>
      </div>

      <div className="flex w-full flex-col gap-4 lg:max-w-3xl lg:flex-1">
        <EventFormBasics
          values={values}
          onChange={patch}
          errors={errors}
          canTagOfficial={canTagOfficial}
          canTagClub={canTagClub}
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
            typeLocked={
              values.eventType === EventType.Official || values.eventType === EventType.Club
            }
          />
        </CollapsibleCard>

        <CollapsibleCard
          title="tags"
          summary={
            values.tagIds.length > 0
              ? `${String(values.tagIds.length)} tag${values.tagIds.length === 1 ? '' : 's'}`
              : undefined
          }
        >
          <EventFormTags values={values} onChange={patch} />
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
            className="border-destructive-border bg-destructive-subtle text-destructive rounded-[var(--radius-md)] border p-3 text-sm"
          >
            {serverError}
          </p>
        ) : null}

        <div className="bg-background fixed inset-x-0 bottom-0 z-50 flex flex-row gap-2 px-4 py-3 sm:static sm:z-auto sm:mx-0 sm:justify-end sm:bg-transparent sm:p-0 sm:pt-2">
          <Button
            variant="secondary"
            onClick={() => void navigate(-1)}
            disabled={saving}
            type="button"
            className="flex-1"
          >
            cancel
          </Button>
          {!existing || isDraft ? (
            <Button
              variant="secondary"
              onClick={() => void submit('draft')}
              disabled={saving}
              type="button"
              className="flex-1"
            >
              save
            </Button>
          ) : null}
          <Button type="submit" disabled={saving} className="flex-1">
            {saving ? 'saving…' : !existing || isDraft ? 'publish' : 'save'}
          </Button>
        </div>
      </div>
      {confirmElement}
    </form>
  );
}
