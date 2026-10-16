import type { EventFormValues } from '@/api/eventWrites';
import { TextField } from '@/components/ui/TextField';
import { Toggle } from '@/components/ui/Toggle';
import { isOfficialOrClub } from '@/models/event';

import { LockIcon } from './LockIcon';

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  errors: Partial<Record<keyof EventFormValues, string>>;
}

export function EventFormRsvp({ values, onChange, errors }: Props) {
  const rsvpOn = values.rsvpEnabled;
  // Older official/club events that still have +1s on stay unlocked so hosts can turn them off.
  const plusOnesLocked = isOfficialOrClub(values.eventType) && !values.allowPlusOnes;

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
          <div className="flex flex-col gap-1">
            <Toggle
              label="allow +1s"
              checked={values.allowPlusOnes}
              disabled={plusOnesLocked}
              onChange={(checked) => {
                onChange({ allowPlusOnes: checked });
              }}
            />
            {plusOnesLocked ? (
              <p className="text-foreground-secondary flex items-center gap-1 text-xs">
                <LockIcon className="h-3.5 w-3.5 shrink-0" />
                +1s are off for official and club pda events
              </p>
            ) : null}
          </div>
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
