import { format } from 'date-fns';
import { enUS } from 'date-fns/locale/en-US';
import { useEffect, useRef, useState } from 'react';
import { DayPicker } from 'react-day-picker';

interface Props {
  label: string;
  value: string | null;
  onChange: (isoDate: string | null) => void;
  disabled?: boolean;
  error?: string | undefined;
}

function isoToDate(iso: string | null): Date | undefined {
  if (!iso) return undefined;
  const d = new Date(`${iso}T00:00:00`);
  return isNaN(d.getTime()) ? undefined : d;
}

function dateToIso(date: Date): string {
  return format(date, 'yyyy-MM-dd');
}

export function DatePicker({ label, value, onChange, disabled, error }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selectedDate = isoToDate(value);

  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onClick);
    return () => {
      document.removeEventListener('mousedown', onClick);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const display = selectedDate ? format(selectedDate, 'EEEE, MMMM d, yyyy').toLowerCase() : '';

  return (
    <div ref={ref} className="relative flex flex-col gap-1">
      <label className="text-foreground text-sm font-medium">{label}</label>

      <button
        type="button"
        disabled={disabled}
        onClick={() => {
          if (!disabled) setOpen((v) => !v);
        }}
        aria-expanded={open}
        className={[
          'h-10 w-full rounded-[var(--radius-md)] border px-3 text-left text-sm transition-colors outline-none',
          display
            ? 'border-brand-200 bg-brand-50 text-brand-900 font-medium'
            : 'border-border-strong bg-surface text-muted-foreground',
          error && 'border-destructive bg-destructive-subtle text-destructive',
          disabled && 'bg-surface-dim text-muted-foreground',
        ].join(' ')}
      >
        {display || 'pick a date'}
      </button>

      {open && (
        <div className="border-brand-100 bg-surface absolute z-50 mt-2 rounded-[var(--radius-md)] border p-3 shadow-(--shadow-lg)">
          <DayPicker
            mode="single"
            selected={selectedDate}
            onSelect={(day) => {
              if (!day) return;
              onChange(dateToIso(day));
              setOpen(false);
            }}
            defaultMonth={selectedDate ?? new Date()}
            locale={enUS}
          />
        </div>
      )}

      {error ? <p className="text-destructive text-xs">{error}</p> : null}
    </div>
  );
}
