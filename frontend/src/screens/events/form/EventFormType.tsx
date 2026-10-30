import type { EventFormValues } from '@/api/eventWrites';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { Toggle } from '@/components/ui/Toggle';
import { EventFormat, EventType, EventVisibility, isOfficialOrClub } from '@/models/event';

const FORMAT_OPTIONS = [
  { value: EventFormat.Walk, label: 'walk' },
  { value: EventFormat.Restaurant, label: 'restaurant' },
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
          name="event-format"
          ariaLabel="event format"
          options={FORMAT_OPTIONS}
          value={values.eventFormat}
          onChange={(eventFormat) => {
            onChange({ eventFormat });
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
