import { RsvpStatus } from '@/models/event';
import { cn } from '@/utils/cn';

type RsvpInputStatus = (typeof RsvpStatus)[keyof typeof RsvpStatus];

const PILLS: { status: RsvpInputStatus; label: string }[] = [
  { status: RsvpStatus.Attending, label: "i'm going" },
  { status: RsvpStatus.Maybe, label: 'maybe' },
  { status: RsvpStatus.CantGo, label: "can't go" },
];

interface Props {
  value: string | null;
  onSelect: (status: RsvpInputStatus) => void;
  disabled?: boolean;
  labelFor?: (status: RsvpInputStatus, defaultLabel: string) => string;
}

export function RsvpStatusPicker({ value, onSelect, disabled = false, labelFor }: Props) {
  return (
    <div className="flex flex-wrap justify-center gap-2">
      {PILLS.map((p) => {
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
              'inline-flex h-10 items-center rounded-full px-4 text-sm font-medium transition-colors disabled:cursor-not-allowed',
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
