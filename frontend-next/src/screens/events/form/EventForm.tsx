// Event create/edit form.
//
// Layout: hero photo → always-visible (title/when/where) → 4 collapsible
// sections (details, links, money, hosts & invites) → actions.
//
// Photo-first by design: the Flutter app's form opened with a big cover
// banner so the flow feels inviting even before a title is typed. Sections
// collapse by default so simple events don't feel like a chore — summary
// badges on each header show what's already filled in.

import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
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
  'rsvpEnabled',
  'allowPlusOnes',
  'maxAttendees',
  'invitePermission',
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
        await update.mutateAsync(merged);
        if (nextStatus === 'draft') toast.success('saved draft 🌱');
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
      if (nextStatus === 'draft') toast.success('saved draft 🌱');
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
  const hostsCount = coHosts.length + (values.visibility === 'invite_only' ? invited.length : 0);

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
        photoUrl={existing?.photoUrl ?? (pendingPhoto ? 'pending' : '')}
        photoUpdatedAt={null}
        onCrop={onCropPhoto}
        onDelete={existing || pendingPhoto ? onDeletePhoto : undefined}
        disabled={saving}
      />

      <EventFormBasics values={values} onChange={patch} errors={errors} />

      <CollapsibleCard
        title="details"
        emoji="🌱"
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
      </CollapsibleCard>

      <CollapsibleCard
        title="links"
        emoji="🔗"
        summary={
          linkCount > 0 ? `${String(linkCount)} link${linkCount === 1 ? '' : 's'}` : undefined
        }
        error={hasAnyError(errors, LINK_FIELDS) ? 'needs attention' : undefined}
        forceOpen={hasAnyError(errors, LINK_FIELDS)}
      >
        <EventFormLinks values={values} onChange={patch} errors={errors} />
      </CollapsibleCard>

      <CollapsibleCard title="money" emoji="💸" summary={moneyFilled ? 'added' : undefined}>
        <EventFormMoney values={values} onChange={patch} errors={errors} />
      </CollapsibleCard>

      <CollapsibleCard
        title="hosts & invites"
        emoji="👥"
        summary={
          hostsCount > 0
            ? `${String(hostsCount)} ${hostsCount === 1 ? 'person' : 'people'}`
            : undefined
        }
      >
        <div className="flex flex-col gap-4">
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
        </div>
      </CollapsibleCard>

      {serverError ? (
        <p
          role="alert"
          className="rounded-[var(--radius-md)] border border-red-200 bg-red-50 p-3 text-sm text-red-700"
        >
          {serverError}
        </p>
      ) : null}

      <div className="border-brand-100 bg-brand-50/95 sticky bottom-0 z-10 -mx-4 flex flex-col gap-2 border-t px-4 py-3 backdrop-blur sm:static sm:mx-0 sm:flex-row sm:justify-end sm:border-0 sm:bg-transparent sm:p-0 sm:pt-2">
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
