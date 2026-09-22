import { addMinutes, format, startOfDay } from 'date-fns';
import { enUS } from 'date-fns/locale/en-US';
import { useEffect, useRef, useState } from 'react';
import { DayPicker } from 'react-day-picker';

interface Props {
  label: string;
  value: string | null;
  onChange: (iso: string | null) => void;
  disabled?: boolean;
  error?: string | undefined;
  optional?: boolean;
  /** Disable calendar days before today (inclusive). For event start times. */
  disablePast?: boolean;
  /** Disable calendar days strictly before this date (the date itself stays selectable). */
  minDate?: Date | null;
  /** Fallback day when no value is set: opens the calendar on its month and prefills its time. */
  defaultDate?: Date | null;
}

function clampAfter(iso: string, minDate: Date | null | undefined): string {
  if (!minDate || new Date(iso) > minDate) return iso;
  return addMinutes(minDate, 30).toISOString();
}

function isoToDate(iso: string | null): Date | undefined {
  if (!iso) return undefined;
  const d = new Date(iso);
  return isNaN(d.getTime()) ? undefined : d;
}

function dateToIso(date: Date, hours: number, minutes: number): string {
  const copy = new Date(date);
  copy.setHours(hours, minutes, 0, 0);
  return copy.toISOString();
}

export function DateTimePicker({
  label,
  value,
  onChange,
  disabled,
  error,
  optional,
  disablePast,
  minDate,
  defaultDate,
}: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selectedDate = isoToDate(value);
  const baseDate = selectedDate ?? defaultDate;
  // Start-of-today so "today" itself is still selectable.
  const todayStart = startOfDay(new Date());
  const dayMatcher = minDate
    ? { before: startOfDay(minDate) }
    : disablePast
      ? { before: todayStart }
      : undefined;

  // Close on outside click
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

  // Close on Escape
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

  const display = value
    ? (() => {
        const d = new Date(value);
        if (isNaN(d.getTime())) return '';
        return format(d, 'EEEE, MMMM d · h:mmaaa').toLowerCase();
      })()
    : '';

  return (
    <div ref={ref} className="relative flex flex-col gap-1">
      <label className="text-foreground text-sm font-medium">
        {label}
        {optional && (
          <span className="text-muted-foreground ml-1 text-xs font-normal">(optional)</span>
        )}
      </label>

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
        {display || 'pick a date & time'}
      </button>

      {open && (
        <div className="border-brand-100 bg-surface absolute z-50 mt-2 rounded-[var(--radius-md)] border p-3 shadow-(--shadow-lg)">
          <DayPicker
            mode="single"
            selected={selectedDate}
            onSelect={(day) => {
              if (!day) return;
              const h = baseDate?.getHours() ?? 12;
              const m = baseDate?.getMinutes() ?? 0;
              onChange(clampAfter(dateToIso(day, h, m), minDate));
            }}
            defaultMonth={selectedDate ?? minDate ?? baseDate ?? new Date()}
            locale={enUS}
            disabled={dayMatcher}
          />
          <div className="border-border mt-2 flex items-center gap-2 border-t pt-2">
            <label htmlFor="dt-time" className="text-muted text-xs">
              time
            </label>
            <input
              id="dt-time"
              type="time"
              value={
                baseDate
                  ? `${String(baseDate.getHours()).padStart(2, '0')}:${String(baseDate.getMinutes()).padStart(2, '0')}`
                  : '12:00'
              }
              onChange={(e) => {
                const [h, m] = e.target.value.split(':').map(Number) as [number, number];
                // Clearing yields [''] → [0, undefined]; ignore empty/unparseable input.
                if (!Number.isFinite(h) || !Number.isFinite(m)) return;
                onChange(clampAfter(dateToIso(baseDate ?? new Date(), h, m), minDate));
              }}
              className="border-border bg-surface focus:border-brand-500 focus:ring-brand-200 h-8 rounded-md border px-2 text-base outline-none focus:ring-1 md:text-sm"
            />
          </div>
        </div>
      )}

      {error ? <p className="text-destructive text-xs">{error}</p> : null}
    </div>
  );
}
