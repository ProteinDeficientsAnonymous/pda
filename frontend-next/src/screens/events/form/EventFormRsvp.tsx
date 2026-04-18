// RSVP settings + capacity.

import type { EventFormValues } from '@/api/eventWrites';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
}

export function EventFormRsvp({ values, onChange }: Props) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-xs font-medium tracking-wide text-neutral-500 uppercase">rsvp</h2>
      <label className="flex items-center justify-between gap-3">
        <span className="text-sm">enable rsvp</span>
        <input
          type="checkbox"
          checked={values.rsvpEnabled}
          onChange={(e) => {
            onChange({ rsvpEnabled: e.target.checked });
          }}
        />
      </label>
      <label className="flex items-center justify-between gap-3">
        <span className="text-sm">allow +1s</span>
        <input
          type="checkbox"
          checked={values.allowPlusOnes}
          onChange={(e) => {
            onChange({ allowPlusOnes: e.target.checked });
          }}
        />
      </label>
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
    </section>
  );
}
