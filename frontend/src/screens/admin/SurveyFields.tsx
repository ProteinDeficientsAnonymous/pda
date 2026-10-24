import { format } from 'date-fns';

import { useEvents } from '@/api/events';
import type { SurveyInput } from '@/api/surveyAdmin';
import { DateTimePicker } from '@/components/ui/DateTimePicker';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { TextField } from '@/components/ui/TextField';
import { type Event, EventType, type EventTypeValue } from '@/models/event';

export type SurveyFormValues = Omit<SurveyInput, 'isActive'>;

interface Props {
  values: SurveyFormValues;
  onChange: (patch: Partial<SurveyFormValues>) => void;
  slugError?: string | undefined;
  linkedEventError?: string | undefined;
  feedbackTypeError?: string | undefined;
  anonymousLocked?: boolean;
}

const VISIBILITY_OPTIONS = [
  { value: 'members_only', label: 'members only' },
  { value: 'public', label: 'public' },
];

const FEEDBACK_TYPE_OPTIONS: { value: '' | EventTypeValue; label: string }[] = [
  { value: '', label: 'not a feedback survey' },
  { value: EventType.Official, label: 'official events' },
  { value: EventType.Club, label: 'club events' },
];

export function SurveyFields({
  values,
  onChange,
  slugError,
  linkedEventError,
  feedbackTypeError,
  anonymousLocked = false,
}: Props) {
  const isFeedback = values.feedbackEventType !== '';
  const anonymous = values.anonymous || isFeedback;
  return (
    <>
      <TextField
        label="title"
        labelSuffix="· required"
        value={values.title}
        onChange={(e) => {
          onChange({ title: e.target.value });
        }}
        maxLength={200}
      />
      <TextField
        label="slug"
        labelSuffix="· required"
        value={values.slug}
        onChange={(e) => {
          onChange({ slug: e.target.value });
        }}
        hint="short url segment — /surveys/:slug"
        error={slugError}
        maxLength={100}
      />
      <Textarea
        label="description"
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
        disabled={isFeedback}
      />
      <Select
        label="feedback survey for"
        value={values.feedbackEventType}
        onChange={(e) => {
          const picked = FEEDBACK_TYPE_OPTIONS.find((o) => o.value === e.target.value);
          const feedbackEventType = picked?.value ?? '';
          onChange(
            feedbackEventType
              ? { feedbackEventType, anonymous: true, linkedEventId: null }
              : { feedbackEventType },
          );
        }}
        options={FEEDBACK_TYPE_OPTIONS}
        error={feedbackTypeError}
      />
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={values.oneResponsePerUser && !anonymous}
          disabled={anonymous}
          onChange={(e) => {
            onChange({ oneResponsePerUser: e.target.checked });
          }}
        />
        <span>
          one response per user
          {anonymous ? (
            <span className="text-muted"> — not enforced on anonymous surveys</span>
          ) : null}
        </span>
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={anonymous}
          disabled={anonymousLocked || isFeedback}
          onChange={(e) => {
            onChange({ anonymous: e.target.checked });
          }}
        />
        <span>
          anonymous responses
          {isFeedback ? (
            <span className="text-muted"> — always anonymous for feedback surveys</span>
          ) : anonymousLocked ? (
            <span className="text-muted"> — locked once responses come in</span>
          ) : null}
        </span>
      </label>
      <Textarea
        label="confirmation message"
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
        />
        <DateTimePicker
          label="closes at"
          value={values.closesAt}
          onChange={(closesAt) => {
            onChange({ closesAt });
          }}
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
        hint="leave blank for unlimited"
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
  disabled,
}: {
  value: string | null;
  onChange: (id: string | null) => void;
  error?: string | undefined;
  disabled?: boolean;
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
      disabled={disabled}
    />
  );
}
