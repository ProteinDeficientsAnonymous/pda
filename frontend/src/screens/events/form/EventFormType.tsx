import type { EventFormValues } from '@/api/eventWrites';
import { Toggle } from '@/components/ui/Toggle';
import { EventType, EventVisibility } from '@/models/event';

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  canTagOfficial: boolean;
  canTagClub: boolean;
}

// event_type is a single value, so the two toggles are mutually exclusive:
// turning one on switches the type (and forces public); turning it off reverts
// to community. Official/club are public-only, hence the forced visibility.
export function EventFormType({ values, onChange, canTagOfficial, canTagClub }: Props) {
  if (!canTagOfficial && !canTagClub) return null;

  const setType = (type: EventFormValues['eventType']) => {
    onChange({ eventType: type, visibility: EventVisibility.Public });
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
