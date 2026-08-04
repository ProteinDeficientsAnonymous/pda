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
            // Not type="number": a focused one steps on wheel/arrow keys (issue 1264).
            type="text"
            inputMode="numeric"
            value={values.maxAttendees === null ? '' : String(values.maxAttendees)}
            onChange={(e) => {
              const digits = e.target.value.replace(/\D/g, '');
              onChange({ maxAttendees: digits === '' ? null : Number(digits) });
            }}
            error={errors.maxAttendees}
          />
        </>
      ) : null}
    </div>
  );
}
