import type { AutosaveStatus as Status } from '@/hooks/useAutosave';
import { cn } from '@/utils/cn';

interface Props {
  status: Status;
  className?: string;
}

const LABELS: Record<Status, string> = {
  idle: '',
  saving: 'saving…',
  saved: 'saved ✓',
  error: "couldn't save",
};

export function AutosaveStatus({ status, className }: Props) {
  const label = LABELS[status];
  if (!label) return null;
  return (
    <span
      aria-live="polite"
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs',
        status === 'saved' && 'bg-success-subtle text-success',
        status === 'saving' && 'bg-surface-dim text-foreground-tertiary',
        status === 'error' && 'bg-destructive-subtle text-destructive',
        className,
      )}
    >
      {label}
    </span>
  );
}
