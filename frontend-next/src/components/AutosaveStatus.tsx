import { cn } from '@/utils/cn';
import type { AutosaveStatus as Status } from '@/hooks/useAutosave';

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
        status === 'saved' && 'bg-green-100 text-green-800',
        status === 'saving' && 'bg-neutral-100 text-neutral-600',
        status === 'error' && 'bg-red-100 text-red-700',
        className,
      )}
    >
      {label}
    </span>
  );
}
