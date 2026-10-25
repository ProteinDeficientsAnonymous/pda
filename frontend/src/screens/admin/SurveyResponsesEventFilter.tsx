import { useEffect, useMemo } from 'react';

import type { SurveyResponseAdmin } from '@/api/surveyAdmin';
import { Select } from '@/components/ui/Select';

import { ALL_EVENTS, eventOptions } from './surveyResponseEvents';

export function SurveyResponsesEventFilter({
  responses,
  value,
  onChange,
}: {
  responses: SurveyResponseAdmin[];
  value: string;
  onChange: (eventId: string) => void;
}) {
  const options = useMemo(
    () => [{ value: ALL_EVENTS, label: 'all events' }, ...eventOptions(responses)],
    [responses],
  );

  useEffect(() => {
    if (!options.some((o) => o.value === value)) onChange(ALL_EVENTS);
  }, [options, value, onChange]);

  return (
    <div className="mb-4 max-w-xs">
      <Select
        label="event"
        hideLabel
        value={value}
        options={options}
        onChange={(e) => {
          onChange(e.target.value);
        }}
      />
    </div>
  );
}
