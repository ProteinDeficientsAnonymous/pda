// "details" section — description + visibility choice.
// Rendered inside a CollapsibleCard by the parent form; this component only
// owns the body layout.
//
// The visibility helper text below the select clarifies that "public" only
// means listed-publicly — location, links, and rsvp are still members-only
// regardless of choice. See EventMemberSection (the public/auth gate).

import type { EventFormValues, VisibilityChoice } from '@/api/eventWrites';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';

const VISIBILITY_OPTIONS: { value: VisibilityChoice; label: string; officialOnly?: boolean }[] = [
  { value: 'public', label: 'public' },
  { value: 'members_only', label: 'members only' },
  { value: 'invite_only', label: 'invite only' },
  { value: 'official', label: 'official (pda-organized)', officialOnly: true },
];

const VISIBILITY_HELPER: Record<VisibilityChoice, string> = {
  members_only: 'only signed-in members can see this event',
  public:
    'anyone can see this in the calendar — but only members can see location, links, and rsvp',
  invite_only:
    'only the people you invite can see this event — you can send invites from the event page after saving',
  official:
    'publicly listed as an official pda event — only members can see location, links, and rsvp',
};

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

      <div className="flex flex-col gap-1">
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
        <p className="text-foreground-secondary text-xs">
          {VISIBILITY_HELPER[values.visibilityChoice]}
        </p>
      </div>
    </div>
  );
}
