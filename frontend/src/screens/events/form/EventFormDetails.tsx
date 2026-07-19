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
  // Locked when the event is a public-only type (official/club) — visibility is
  // forced to public and shown as a locked read-out instead of the dropdown.
  typeLocked: boolean;
}

export function EventFormDetails({ values, onChange, errors, typeLocked }: Props) {
  const helper = typeLocked
    ? 'official and club pda events are always public'
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

      {typeLocked ? (
        <LockedVisibility helper={helper} />
      ) : (
        <div className="flex flex-col gap-1">
          <Select
            label="who can see it"
            value={values.visibility}
            onChange={(e) => {
              onChange({ visibility: e.target.value as Visibility });
            }}
            options={VISIBILITY_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
          />
          <p className="text-foreground-secondary text-xs">{helper}</p>
        </div>
      )}
    </div>
  );
}

function LockIcon({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 20 20"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="4.5" y="9" width="11" height="7.5" rx="1.5" />
      <path d="M7 9V6.5a3 3 0 0 1 6 0V9" />
    </svg>
  );
}

// Forced-public event types show a locked read-out instead of the dropdown so the constraint reads visually.
function LockedVisibility({ helper }: { helper: string }) {
  return (
    <div
      className="flex flex-col gap-1"
      role="group"
      aria-label="who can see it — locked to public"
    >
      <span className="text-foreground text-sm font-medium" aria-hidden="true">
        who can see it
      </span>
      <div className="border-border-strong bg-surface-dim flex flex-wrap items-center gap-x-2 gap-y-1 rounded-md border px-3 py-2 text-sm">
        <LockIcon className="text-foreground-secondary h-4 w-4 shrink-0" />
        <span className="text-foreground font-medium">
          public<span className="sr-only"> — selected, locked</span>
        </span>
        <span className="border-border-strong text-foreground-secondary ml-auto rounded-full border px-2 py-0.5 text-xs">
          locked
        </span>
      </div>
      <p className="text-foreground-secondary text-xs">{helper}</p>
    </div>
  );
}
