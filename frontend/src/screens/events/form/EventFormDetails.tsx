// "details" section — description + visibility choice.
// Rendered inside a CollapsibleCard by the parent form; this component only
// owns the body layout.
//
// The visibility helper text below the select clarifies that "public" only
// means listed-publicly — location, links, and rsvp are still members-only
// regardless of choice. See EventMemberSection (the public/auth gate).

import type { EventFormValues } from '@/api/eventWrites';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { EventVisibility } from '@/models/event';

type Visibility = EventFormValues['visibility'];

const VISIBILITY_OPTIONS: { value: Visibility; label: string }[] = [
  { value: EventVisibility.Public, label: 'public' },
  { value: EventVisibility.MembersOnly, label: 'members only' },
  { value: EventVisibility.InviteOnly, label: 'invite only' },
];

const VISIBILITY_HELPER: Record<Visibility, string> = {
  members_only: 'only signed-in members can see this event',
  public:
    'anyone can see this in the calendar — but only members can see location, links, and rsvp',
  invite_only:
    'only the people you invite can see this event — you can send invites from the event page after saving',
};

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  errors: Partial<Record<keyof EventFormValues, string>>;
  // Locked when the event is a public-only type (official) — visibility is
  // forced to public and the select is disabled.
  typeLocked: boolean;
}

export function EventFormDetails({ values, onChange, errors, typeLocked }: Props) {
  const helper = typeLocked
    ? 'official pda events are always public'
    : VISIBILITY_HELPER[values.visibility];

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
          value={values.visibility}
          disabled={typeLocked}
          onChange={(e) => {
            onChange({ visibility: e.target.value as Visibility });
          }}
          options={VISIBILITY_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
        />
        <p className="text-foreground-secondary text-xs">{helper}</p>
      </div>
    </div>
  );
}
