import type { EventFormValues } from '@/api/eventWrites';
import { Toggle } from '@/components/ui/Toggle';
import { EventType, EventVisibility } from '@/models/event';

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  canTagOfficial: boolean;
}

export function EventFormType({ values, onChange, canTagOfficial }: Props) {
  if (!canTagOfficial) return null;

  return (
    <Toggle
      label="make it an official pda event"
      checked={values.eventType === EventType.Official}
      onChange={(checked) => {
        onChange(
          checked
            ? { eventType: EventType.Official, visibility: EventVisibility.Public }
            : { eventType: EventType.Community },
        );
      }}
    />
  );
}
