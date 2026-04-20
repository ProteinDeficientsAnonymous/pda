// "details" section — description + visibility choice.
// Rendered inside a CollapsibleCard by the parent form; this component only
// owns the body layout.

import type { EventFormValues, VisibilityChoice } from '@/api/eventWrites';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';

const VISIBILITY_OPTIONS: { value: VisibilityChoice; label: string; officialOnly?: boolean }[] = [
  { value: 'members_only', label: 'members only' },
  { value: 'public', label: 'public' },
  { value: 'invite_only', label: 'invite only' },
  { value: 'official', label: 'official (pda-organized)', officialOnly: true },
];

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  errors: Partial<Record<keyof EventFormValues, string>>;
  canTagOfficial: boolean;
}

export function EventFormDetails({ values, onChange, errors, canTagOfficial }: Props) {
  const visibleOptions = VISIBILITY_OPTIONS.filter((o) => !o.officialOnly || canTagOfficial);

  return (
    <div className="flex flex-col gap-4">
      <Textarea
        label="description"
        value={values.description}
        onChange={(e) => {
          onChange({ description: e.target.value });
        }}
        maxLength={2000}
        placeholder="tell people what this is about"
        error={errors.description}
      />

      <Select
        label="who can see it"
        value={values.visibilityChoice}
        onChange={(e) => {
          const choice = e.target.value as VisibilityChoice;
          const { visibility, eventType } = (() => {
            if (choice === 'official')
              return { visibility: 'public' as const, eventType: 'official' as const };
            return { visibility: choice, eventType: 'community' as const };
          })();
          onChange({ visibilityChoice: choice, visibility, eventType });
        }}
        options={visibleOptions.map((o) => ({ value: o.value, label: o.label }))}
      />
    </div>
  );
}
