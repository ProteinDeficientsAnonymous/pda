import type { RsvpInputStatus } from '@/models/event';
import { RSVP_STATUS_LABELS } from '@/models/event';
import { cn } from '@/utils/cn';

interface Props {
  value: string | null;
  onSelect: (status: RsvpInputStatus) => void;
  disabled?: boolean;
  labelFor?: (status: RsvpInputStatus, defaultLabel: string) => string;
  statuses?: RsvpInputStatus[];
  prominent?: boolean;
}

export function RsvpStatusPicker({
  value,
  onSelect,
  disabled = false,
  labelFor,
  statuses,
  prominent = false,
}: Props) {
  const options = statuses
    ? RSVP_STATUS_LABELS.filter((p) => statuses.includes(p.status))
    : RSVP_STATUS_LABELS;
  return (
    <div className="-mx-1 flex justify-center-safe gap-2 overflow-x-auto px-1 py-1">
      {options.map((p) => {
        const label = labelFor ? labelFor(p.status, p.label) : p.label;
        const active = value === p.status;
        return (
          <button
            key={p.status}
            type="button"
            aria-pressed={active}
            disabled={disabled}
            onClick={() => {
              onSelect(p.status);
            }}
            className={cn(
              'inline-flex shrink-0 items-center justify-center rounded-full font-medium transition-colors disabled:cursor-not-allowed',
              prominent ? 'h-12 flex-1 px-5 text-base' : 'h-10 px-4 text-sm',
              active
                ? 'bg-brand-600 text-brand-on'
                : 'border-border-strong text-foreground-secondary hover:bg-background border',
              disabled && 'opacity-60',
            )}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
