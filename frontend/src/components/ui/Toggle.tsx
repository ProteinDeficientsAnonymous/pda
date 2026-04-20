import { cn } from '@/utils/cn';

interface Props {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label: string;
  className?: string;
}

export function Toggle({ checked, onChange, disabled, label, className }: Props) {
  return (
    <label className={cn('flex items-center justify-between gap-3 py-1', className)}>
      <span className="text-foreground text-sm">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => {
          onChange(!checked);
        }}
        className={cn(
          'focus-visible:ring-brand-300 relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full transition-colors duration-200 focus-visible:ring-2 focus-visible:outline-none',
          checked ? 'bg-brand-600' : 'bg-toggle-off',
          disabled && 'cursor-not-allowed opacity-50',
        )}
      >
        <span
          className={cn(
            'pointer-events-none inline-block h-4 w-4 translate-y-0.5 rounded-full bg-white shadow-(--shadow-sm) transition-transform duration-200',
            checked ? 'translate-x-[18px]' : 'translate-x-0.5',
          )}
        />
      </button>
    </label>
  );
}
