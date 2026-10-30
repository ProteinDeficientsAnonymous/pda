import type { EventFormValues } from '@/api/eventWrites';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { Toggle } from '@/components/ui/Toggle';
import { EventType, EventVisibility, isOfficialOrClub, OfficialKind } from '@/models/event';

const KIND_OPTIONS = [
  { value: OfficialKind.Walk, label: 'walk' },
  { value: OfficialKind.Restaurant, label: 'restaurant' },
];

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  canTagOfficial: boolean;
  canTagClub: boolean;
}

// Single-valued event_type makes the toggles mutually exclusive; official/club force public and lock +1s off.
export function EventFormType({ values, onChange, canTagOfficial, canTagClub }: Props) {
  if (!canTagOfficial && !canTagClub) return null;

  const setType = (type: EventFormValues['eventType']) => {
    onChange({
      eventType: type,
      ...(isOfficialOrClub(type)
        ? { visibility: EventVisibility.Public, allowPlusOnes: false }
        : {}),
    });
  };

  return (
    <div className="flex flex-col gap-1">
      {canTagOfficial ? (
        <Toggle
          label="make it an official pda event"
          checked={values.eventType === EventType.Official}
          onChange={(checked) => {
            setType(checked ? EventType.Official : EventType.Community);
          }}
        />
      ) : null}
      {canTagOfficial && values.eventType === EventType.Official ? (
        <SegmentedControl
          name="official-kind"
          ariaLabel="kind of event"
          options={KIND_OPTIONS}
          value={values.officialKind}
          onChange={(officialKind) => {
            onChange({ officialKind });
          }}
        />
      ) : null}
      {canTagClub ? (
        <Toggle
          label="make it a pda club event"
          checked={values.eventType === EventType.Club}
          onChange={(checked) => {
            setType(checked ? EventType.Club : EventType.Community);
          }}
        />
      ) : null}
    </div>
  );
}
