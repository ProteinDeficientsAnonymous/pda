import type { EventFormValues } from '@/api/eventWrites';
import { Toggle } from '@/components/ui/Toggle';
import { EventType, EventVisibility } from '@/models/event';

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  canTagOfficial: boolean;
  canTagClub: boolean;
}

// Single-valued event_type makes the toggles mutually exclusive; only official/club force public.
export function EventFormType({ values, onChange, canTagOfficial, canTagClub }: Props) {
  if (!canTagOfficial && !canTagClub) return null;

  const setType = (type: EventFormValues['eventType']) => {
    const isPublicOnly = type === EventType.Official || type === EventType.Club;
    onChange({
      eventType: type,
      ...(isPublicOnly ? { visibility: EventVisibility.Public } : {}),
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
