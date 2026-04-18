// "details" section — description + visibility + event type + rsvp controls.
// Rendered inside a CollapsibleCard by the parent form; this component only
// owns the body layout.

import type { EventFormValues } from '@/api/eventWrites';
import { RichEditor } from '@/components/RichEditor/RichEditor';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  errors: Partial<Record<keyof EventFormValues, string>>;
  canTagOfficial: boolean;
}

export function EventFormDetails({ values, onChange, errors, canTagOfficial }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <label
          htmlFor="event-description"
          className="mb-1 block text-sm font-medium text-neutral-800"
        >
          description
        </label>
        <div id="event-description">
          <RichEditor
            value={''}
            onChange={(pm) => {
              onChange({ description: pm });
            }}
            placeholder="tell people what this is about"
          />
        </div>
        {errors.description ? (
          <p className="mt-1 text-xs text-red-600">{errors.description}</p>
        ) : null}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Select
          label="visibility"
          value={values.visibility}
          onChange={(e) => {
            onChange({ visibility: e.target.value as EventFormValues['visibility'] });
          }}
          options={[
            { value: 'public', label: 'public' },
            { value: 'members_only', label: 'members only' },
            { value: 'invite_only', label: 'invite only' },
          ]}
        />
        <Select
          label="event type"
          value={values.eventType}
          onChange={(e) => {
            onChange({ eventType: e.target.value as EventFormValues['eventType'] });
          }}
          options={[
            { value: 'community', label: 'community' },
            ...(canTagOfficial ? [{ value: 'official', label: 'official (pda-organized)' }] : []),
          ]}
        />
      </div>

      <div className="bg-brand-50/50 rounded-[var(--radius-md)] p-3">
        <p className="text-brand-800 mb-2 text-xs font-medium tracking-wide uppercase">rsvp</p>
        <label className="flex items-center justify-between gap-3 py-1">
          <span className="text-sm text-neutral-800">enable rsvp</span>
          <input
            type="checkbox"
            checked={values.rsvpEnabled}
            onChange={(e) => {
              onChange({ rsvpEnabled: e.target.checked });
            }}
            className="accent-brand-600"
          />
        </label>
        <label className="flex items-center justify-between gap-3 py-1">
          <span className="text-sm text-neutral-800">allow +1s</span>
          <input
            type="checkbox"
            checked={values.allowPlusOnes}
            onChange={(e) => {
              onChange({ allowPlusOnes: e.target.checked });
            }}
            className="accent-brand-600"
          />
        </label>
        <div className="mt-2">
          <TextField
            label="max attendees (optional)"
            type="number"
            min={0}
            value={values.maxAttendees === null ? '' : String(values.maxAttendees)}
            onChange={(e) => {
              const v = e.target.value;
              onChange({ maxAttendees: v === '' ? null : Number(v) });
            }}
          />
        </div>
      </div>

      {values.visibility === 'invite_only' ? (
        <Select
          label="who can invite"
          value={values.invitePermission}
          onChange={(e) => {
            onChange({
              invitePermission: e.target.value as EventFormValues['invitePermission'],
            });
          }}
          options={[
            { value: 'all_members', label: 'all members' },
            { value: 'co_hosts_only', label: 'co-hosts only' },
          ]}
        />
      ) : null}
    </div>
  );
}
