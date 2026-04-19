// Always-visible zone: title, start + end, tbd toggle, location.
// Description / visibility / event type moved into the details section.

import type { EventFormValues } from '@/api/eventWrites';
import { DateTimePicker } from '@/components/ui/DateTimePicker';
import { LocationField } from '@/components/ui/LocationField';
import { TextField } from '@/components/ui/TextField';
import { Toggle } from '@/components/ui/Toggle';

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  errors: Partial<Record<keyof EventFormValues, string>>;
  timeLocked?: boolean;
}

export function EventFormBasics({ values, onChange, errors, timeLocked = false }: Props) {
  return (
    <div className="flex flex-col gap-4 rounded-[var(--radius-md)] border border-brand-100 bg-surface p-4 shadow-(--shadow-sm)">
      <TextField
        label="title"
        value={values.title}
        onChange={(e) => {
          onChange({ title: e.target.value });
        }}
        maxLength={200}
        placeholder="sunday potluck"
        error={errors.title}
        required
      />

      {timeLocked ? (
        <p className="text-sm text-neutral-600">
          date locked — a poll is active. finalize it to set the time.
        </p>
      ) : (
        <>
          <Toggle
            label="date & time tbd"
            checked={values.datetimeTbd}
            onChange={(checked) => {
              onChange({ datetimeTbd: checked });
            }}
          />

          {!values.datetimeTbd ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <DateTimePicker
                label="starts"
                value={values.startDatetime}
                onChange={(iso) => {
                  onChange({ startDatetime: iso });
                }}
                error={errors.startDatetime}
              />
              <DateTimePicker
                label="ends"
                value={values.endDatetime}
                onChange={(iso) => {
                  onChange({ endDatetime: iso });
                }}
                error={errors.endDatetime}
                optional
              />
            </div>
          ) : null}
        </>
      )}

      <LocationField
        label="location"
        value={values.location}
        latitude={values.latitude}
        longitude={values.longitude}
        onChange={(patch) => {
          onChange(patch);
        }}
        maxLength={300}
        placeholder="address, neighborhood, or 'dm for details'"
        error={errors.location}
      />
    </div>
  );
}