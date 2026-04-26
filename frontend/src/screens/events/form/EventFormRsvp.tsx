// rsvp section — toggles + max attendees.
// Rendered inside its own CollapsibleCard by the parent form.
// When rsvp is off, allow +1s and guests-can-invite are forced off.

import type { EventFormValues } from '@/api/eventWrites';
import { TextField } from '@/components/ui/TextField';
import { Toggle } from '@/components/ui/Toggle';

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  errors: Partial<Record<keyof EventFormValues, string>>;
}

export function EventFormRsvp({ values, onChange, errors }: Props) {
  const rsvpOn = values.rsvpEnabled;

  return (
    <div className="flex flex-col gap-4">
      <Toggle
        label="enable rsvp"
        checked={values.rsvpEnabled}
        onChange={(checked) => {
          if (!checked) {
            onChange({
              rsvpEnabled: false,
              allowPlusOnes: false,
              invitePermission: 'co_hosts_only',
            });
          } else {
            onChange({ rsvpEnabled: true });
          }
        }}
      />
      {rsvpOn ? (
        <>
          <Toggle
            label="allow +1s"
            checked={values.allowPlusOnes}
            onChange={(checked) => {
              onChange({ allowPlusOnes: checked });
            }}
          />
          <Toggle
            label="guests can invite friends"
            checked={values.invitePermission === 'all_members'}
            onChange={(checked) => {
              onChange({ invitePermission: checked ? 'all_members' : 'co_hosts_only' });
            }}
          />
          <TextField
            label="max attendees (optional)"
            type="number"
            inputMode="numeric"
            min={1}
            max={200}
            value={values.maxAttendees === null ? '' : String(values.maxAttendees)}
            onChange={(e) => {
              const v = e.target.value;
              onChange({ maxAttendees: v === '' ? null : Number(v) });
            }}
            error={errors.maxAttendees}
            className="[-moz-appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
          />
        </>
      ) : null}
    </div>
  );
}
