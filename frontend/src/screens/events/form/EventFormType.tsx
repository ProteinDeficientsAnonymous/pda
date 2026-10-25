import type { EventFormValues } from '@/api/eventWrites';
import { Toggle } from '@/components/ui/Toggle';
import { EventType, EventVisibility, isOfficialOrClub } from '@/models/event';

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  canTagOfficial: boolean;
  canTagClub: boolean;
  showWalkToggle?: boolean;
}

// Single-valued event_type makes the toggles mutually exclusive; official/club force public and lock +1s off.
export function EventFormType({
  values,
  onChange,
  canTagOfficial,
  canTagClub,
  showWalkToggle = false,
}: Props) {
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
      {canTagOfficial && showWalkToggle && values.eventType === EventType.Official ? (
        <Toggle
          label="it's a walk"
          checked={values.isWalk}
          onChange={(checked) => {
            onChange({ isWalk: checked });
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
