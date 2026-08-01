import type { DevEventVisibility, DevTestEventOptions } from '@/api/devTools';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { Toggle } from '@/components/ui/Toggle';

interface Props {
  options: DevTestEventOptions;
  onChange: (options: DevTestEventOptions) => void;
}

const VISIBILITY_OPTIONS: { value: DevEventVisibility; label: string }[] = [
  { value: 'public', label: 'public' },
  { value: 'members_only', label: 'members only' },
  { value: 'invite_only', label: 'invite only' },
];

function NumberField({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}) {
  return (
    <TextField
      label={label}
      type="number"
      inputMode="numeric"
      min={0}
      max={50}
      value={String(value)}
      onChange={(e) => {
        onChange(Number(e.target.value));
      }}
      disabled={disabled}
      className="[-moz-appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
    />
  );
}

export function DevTestEventOverrides({ options, onChange }: Props) {
  function set<K extends keyof DevTestEventOptions>(key: K, value: DevTestEventOptions[K]) {
    onChange({ ...options, [key]: value });
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-1">
      <div className="flex flex-col gap-1">
        <Toggle
          label="past event"
          checked={options.isPast}
          onChange={(v) => {
            set('isPast', v);
          }}
        />
        <Toggle
          label="canceled"
          checked={options.isCanceled}
          onChange={(v) => {
            set('isCanceled', v);
          }}
        />
        <Toggle
          label="official event"
          checked={options.isOfficial}
          onChange={(v) => {
            onChange({ ...options, isOfficial: v, isClub: v ? false : options.isClub });
          }}
        />
        <Toggle
          label="club event"
          checked={options.isClub}
          onChange={(v) => {
            onChange({ ...options, isClub: v, isOfficial: v ? false : options.isOfficial });
          }}
        />
        <Toggle
          label="make me a host"
          checked={options.makeMeHost}
          onChange={(v) => {
            onChange({ ...options, makeMeHost: v, makeMeGuest: v ? false : options.makeMeGuest });
          }}
        />
        <Toggle
          label="make me a guest"
          checked={options.makeMeGuest}
          onChange={(v) => {
            onChange({ ...options, makeMeGuest: v, makeMeHost: v ? false : options.makeMeHost });
          }}
        />
        <Toggle
          label="rsvps enabled"
          checked={options.rsvpEnabled}
          onChange={(v) => {
            set('rsvpEnabled', v);
          }}
        />
        <Toggle
          label="allow plus-ones"
          checked={options.allowPlusOnes}
          onChange={(v) => {
            set('allowPlusOnes', v);
          }}
        />
      </div>

      <div className="flex flex-col gap-2">
        <Select
          label="visibility"
          value={options.visibility}
          onChange={(e) => {
            set('visibility', e.target.value as DevEventVisibility);
          }}
          options={VISIBILITY_OPTIONS}
          disabled={options.isOfficial || options.isClub}
        />
        <NumberField
          label="max attendees (0 = unlimited)"
          value={options.maxAttendees ?? 0}
          onChange={(v) => {
            set('maxAttendees', v === 0 ? null : v);
          }}
        />
      </div>

      <div className="flex flex-col gap-2">
        <div className="text-muted-foreground text-xs">
          attendees are filled from existing members (or created if the pool runs out)
        </div>
        <NumberField
          label="going"
          value={options.goingCount}
          onChange={(v) => {
            set('goingCount', v);
          }}
        />
        <NumberField
          label="going (non-members, official events only)"
          value={options.nonMemberGoingCount}
          onChange={(v) => {
            set('nonMemberGoingCount', v);
          }}
          disabled={!options.isOfficial}
        />
        <NumberField
          label="maybe"
          value={options.maybeCount}
          onChange={(v) => {
            set('maybeCount', v);
          }}
        />
        <NumberField
          label="can't go"
          value={options.cantGoCount}
          onChange={(v) => {
            set('cantGoCount', v);
          }}
        />
        <NumberField
          label="invited"
          value={options.invitedCount}
          onChange={(v) => {
            set('invitedCount', v);
          }}
        />
        <NumberField
          label="co-hosts (accepted)"
          value={options.cohostCount}
          onChange={(v) => {
            set('cohostCount', v);
          }}
        />
        <NumberField
          label="co-hosts (invited)"
          value={options.invitedCohostCount}
          onChange={(v) => {
            set('invitedCohostCount', v);
          }}
        />
      </div>

      <div className="flex flex-col gap-2">
        <div className="text-muted-foreground text-xs">cost — leave blank to skip</div>
        <TextField
          label="price"
          value={options.price}
          onChange={(e) => {
            set('price', e.target.value);
          }}
        />
        <TextField
          label="venmo"
          value={options.venmoLink}
          onChange={(e) => {
            set('venmoLink', e.target.value);
          }}
        />
        <TextField
          label="cash app"
          value={options.cashappLink}
          onChange={(e) => {
            set('cashappLink', e.target.value);
          }}
        />
        <TextField
          label="zelle"
          value={options.zelleInfo}
          onChange={(e) => {
            set('zelleInfo', e.target.value);
          }}
        />
      </div>
    </div>
  );
}
