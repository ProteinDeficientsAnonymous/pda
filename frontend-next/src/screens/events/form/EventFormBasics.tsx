// Always-visible zone: title, start + end, tbd toggle, location.
// Description / visibility / event type moved into the details section.

import type { EventFormValues } from '@/api/eventWrites';
import { TextField } from '@/components/ui/TextField';
import { isoToLocalInput, localInputToIso } from './datetimeUtils';

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  errors: Partial<Record<keyof EventFormValues, string>>;
}

export function EventFormBasics({ values, onChange, errors }: Props) {
  return (
    <div className="border-brand-100 flex flex-col gap-4 rounded-[var(--radius-md)] border bg-white p-4 shadow-sm">
      <TextField
        label="title"
        value={values.title}
        onChange={(e) => {
          onChange({ title: e.target.value });
        }}
        maxLength={200}
        placeholder="sunday potluck 🌿"
        error={errors.title}
        required
      />

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
            aria-invalid={errors.startDatetime ? true : undefined}
            className="focus:border-brand-500 focus:ring-brand-200 h-10 w-full rounded-[var(--radius-md)] border border-neutral-300 bg-white px-3 text-sm outline-none focus:ring-2 disabled:bg-neutral-100"
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
            aria-invalid={errors.endDatetime ? true : undefined}
            className="focus:border-brand-500 focus:ring-brand-200 h-10 w-full rounded-[var(--radius-md)] border border-neutral-300 bg-white px-3 text-sm outline-none focus:ring-2 disabled:bg-neutral-100"
          />
          {errors.endDatetime ? (
            <p className="mt-1 text-xs text-red-600">{errors.endDatetime}</p>
          ) : null}
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm text-neutral-700">
        <input
          type="checkbox"
          checked={values.datetimeTbd}
          onChange={(e) => {
            onChange({ datetimeTbd: e.target.checked });
          }}
          className="accent-brand-600"
        />
        <span>date &amp; time tbd</span>
      </label>

      <TextField
        label="location"
        value={values.location}
        onChange={(e) => {
          onChange({ location: e.target.value });
        }}
        maxLength={300}
        placeholder="address, neighborhood, or 'dm for details'"
        error={errors.location}
      />
    </div>
  );
}
