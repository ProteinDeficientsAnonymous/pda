// Basics section: title / description / datetime / tbd toggle.

import { RichEditor } from '@/components/RichEditor/RichEditor';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import type { EventFormValues } from '@/api/eventWrites';
import { isoToLocalInput, localInputToIso } from './datetimeUtils';

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  errors: Partial<Record<keyof EventFormValues, string>>;
  canTagOfficial: boolean;
}

export function EventFormBasics({ values, onChange, errors, canTagOfficial }: Props) {
  return (
    <section className="flex flex-col gap-4">
      <TextField
        label="title"
        value={values.title}
        onChange={(e) => {
          onChange({ title: e.target.value });
        }}
        maxLength={200}
        error={errors.title}
        required
      />

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
            placeholder="event description"
          />
        </div>
        {errors.description ? (
          <p className="mt-1 text-xs text-red-600">{errors.description}</p>
        ) : null}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="event-starts" className="mb-1 block text-sm font-medium text-neutral-800">
            starts
          </label>
          <input
            id="event-starts"
            type="datetime-local"
            value={isoToLocalInput(values.startDatetime)}
            onChange={(e) => {
              onChange({ startDatetime: localInputToIso(e.target.value) ?? '' });
            }}
            disabled={values.datetimeTbd}
            className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200 disabled:bg-neutral-100"
          />
          {errors.startDatetime ? (
            <p className="mt-1 text-xs text-red-600">{errors.startDatetime}</p>
          ) : null}
        </div>
        <div>
          <label htmlFor="event-ends" className="mb-1 block text-sm font-medium text-neutral-800">
            ends (optional)
          </label>
          <input
            id="event-ends"
            type="datetime-local"
            value={isoToLocalInput(values.endDatetime)}
            onChange={(e) => {
              onChange({ endDatetime: localInputToIso(e.target.value) });
            }}
            disabled={values.datetimeTbd}
            className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200 disabled:bg-neutral-100"
          />
          {errors.endDatetime ? (
            <p className="mt-1 text-xs text-red-600">{errors.endDatetime}</p>
          ) : null}
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={values.datetimeTbd}
          onChange={(e) => {
            onChange({ datetimeTbd: e.target.checked });
          }}
        />
        <span>date & time tbd</span>
      </label>

      <TextField
        label="location"
        value={values.location}
        onChange={(e) => {
          onChange({ location: e.target.value });
        }}
        maxLength={300}
        error={errors.location}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Select
          label="visibility"
          value={values.visibility}
          onChange={(e) => {
            onChange({
              visibility: e.target.value as EventFormValues['visibility'],
            });
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
    </section>
  );
}
