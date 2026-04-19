import { cn } from '@/utils/cn';

interface Props<T> {
  name: string;
  ariaLabel: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
}

export function SegmentedControl<T extends string | number>({
  name,
  ariaLabel,
  options,
  value,
  onChange,
  className,
}: Props<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={cn(
        'inline-flex rounded-full border border-border-strong bg-surface p-1',
        className,
      )}
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <label
            key={String(opt.value)}
            className={cn(
              'inline-flex h-8 cursor-pointer items-center rounded-full px-3 text-sm transition-colors',
              active
                ? 'bg-brand-600 text-brand-on'
                : 'text-foreground-secondary hover:bg-surface-dim',
            )}
          >
            <input
              type="radio"
              name={name}
              value={String(opt.value)}
              checked={active}
              onChange={() => {
                onChange(opt.value);
              }}
              className="sr-only"
            />
            {opt.label}
          </label>
        );
      })}
    </div>
  );
}
