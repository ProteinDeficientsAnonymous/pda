import { format } from 'date-fns';

import { useEvents } from '@/api/events';
import type { SurveyInput } from '@/api/surveyAdmin';
import { DateTimePicker } from '@/components/ui/DateTimePicker';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { TextField } from '@/components/ui/TextField';
import type { Event } from '@/models/event';

export type SurveyFormValues = Omit<SurveyInput, 'isActive'>;

interface Props {
  values: SurveyFormValues;
  onChange: (patch: Partial<SurveyFormValues>) => void;
  slugError?: string | undefined;
  linkedEventError?: string | undefined;
  anonymousLocked?: boolean;
}

const VISIBILITY_OPTIONS = [
  { value: 'members_only', label: 'members only' },
  { value: 'public', label: 'public' },
];

export function SurveyFields({
  values,
  onChange,
  slugError,
  linkedEventError,
  anonymousLocked = false,
}: Props) {
  return (
    <>
      <TextField
        label="title"
        value={values.title}
        onChange={(e) => {
          onChange({ title: e.target.value });
        }}
        maxLength={200}
      />
      <TextField
        label="slug"
        value={values.slug}
        onChange={(e) => {
          onChange({ slug: e.target.value });
        }}
        hint="short url segment — /surveys/:slug"
        error={slugError}
        maxLength={100}
      />
      <Textarea
        label="description (optional)"
        value={values.description}
        onChange={(e) => {
          onChange({ description: e.target.value });
        }}
        rows={3}
        maxLength={2000}
      />
      <Select
        label="visibility"
        value={values.visibility}
        onChange={(e) => {
          onChange({ visibility: e.target.value });
        }}
        options={VISIBILITY_OPTIONS}
      />
      <LinkedEventSelect
        value={values.linkedEventId}
        onChange={(linkedEventId) => {
          onChange({ linkedEventId });
        }}
        error={linkedEventError}
      />
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={values.oneResponsePerUser && !values.anonymous}
          disabled={values.anonymous}
          onChange={(e) => {
            onChange({ oneResponsePerUser: e.target.checked });
          }}
        />
        <span>
          one response per user
          {values.anonymous ? (
            <span className="text-muted"> — not enforced on anonymous surveys</span>
          ) : null}
        </span>
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={values.anonymous}
          disabled={anonymousLocked}
          onChange={(e) => {
            onChange({ anonymous: e.target.checked });
          }}
        />
        <span>
          anonymous responses
          {anonymousLocked ? (
            <span className="text-muted"> — locked once responses come in</span>
          ) : null}
        </span>
      </label>
      <Textarea
        label="confirmation message (optional)"
        value={values.confirmationMessage}
        onChange={(e) => {
          onChange({ confirmationMessage: e.target.value });
        }}
        hint="shown to the participant after they submit"
        rows={2}
        maxLength={1000}
      />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <DateTimePicker
          label="opens at"
          value={values.opensAt}
          onChange={(opensAt) => {
            onChange({ opensAt });
          }}
          optional
        />
        <DateTimePicker
          label="closes at"
          value={values.closesAt}
          onChange={(closesAt) => {
            onChange({ closesAt });
          }}
          optional
        />
      </div>
      <TextField
        label="max responses"
        type="number"
        min={1}
        value={values.maxResponses ?? ''}
        onChange={(e) => {
          const raw = e.target.value;
          onChange({ maxResponses: raw === '' ? null : Number(raw) });
        }}
        hint="optional — leave blank for unlimited"
      />
    </>
  );
}

function eventLabel(e: Event): string {
  const date = e.startDatetime ? ` · ${format(e.startDatetime, 'MMM d, yyyy').toLowerCase()}` : '';
  return `${e.title.toLowerCase()}${date}`;
}

function LinkedEventSelect({
  value,
  onChange,
  error,
}: {
  value: string | null;
  onChange: (id: string | null) => void;
  error?: string | undefined;
}) {
  const { data: events = [] } = useEvents();
  const options = events.map((e) => ({ value: e.id, label: eventLabel(e) }));
  // A linked event that has left the active list (past, cancelled) must stay selectable.
  if (value && !options.some((o) => o.value === value)) {
    options.unshift({ value, label: 'current linked event' });
  }
  return (
    <Select
      label="linked event"
      value={value ?? ''}
      onChange={(e) => {
        onChange(e.target.value || null);
      }}
      options={[{ value: '', label: 'none' }, ...options]}
      error={error}
    />
  );
}
