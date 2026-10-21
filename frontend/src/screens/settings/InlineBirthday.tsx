import { getDaysInMonth } from 'date-fns';
import { type ReactNode, useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import type { Veganniversary } from '@/models/user';
import { formatBirthday, formatVeganniversary } from '@/utils/datetime';

export interface DateParts {
  month: number;
  day: number | null;
  year: number | null;
}

export interface DateDraft {
  month: number | null;
  day: number | null;
  year: number | null;
}

const VEGANNIVERSARY_HINT =
  "the exact date isn't required, but please let us know at least the month and year!";

const MONTH_OPTIONS = [
  'january',
  'february',
  'march',
  'april',
  'may',
  'june',
  'july',
  'august',
  'september',
  'october',
  'november',
  'december',
].map((name, i) => ({ value: String(i + 1), label: name }));

const NO_YEAR = '';
const CURRENT_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: 120 }, (_, i) => {
  const year = CURRENT_YEAR - i;
  return { value: String(year), label: String(year) };
});
const OPTIONAL_YEAR_OPTIONS = [{ value: NO_YEAR, label: 'prefer not to say' }, ...YEARS];

function daysInMonth(month: number | null, year: number | null) {
  if (!month) return 31;
  return getDaysInMonth(new Date(year ?? 2000, month - 1));
}

function dayOptions(month: number | null, year: number | null) {
  return Array.from({ length: daysInMonth(month, year) }, (_, i) => ({
    value: String(i + 1),
    label: String(i + 1),
  }));
}

function displayValue(value: DateParts, requireDay: boolean, requireYear: boolean): string {
  if (requireYear && value.year != null) {
    return formatVeganniversary({ month: value.month, day: value.day, year: value.year });
  }
  if (requireDay && value.day != null) {
    return formatBirthday({ month: value.month, day: value.day, year: value.year });
  }
  return '';
}

export function InlineBirthday({
  label,
  value,
  onSave,
  placeholder,
  hint,
  requireDay = true,
  requireYear = false,
  onDraftChange,
}: {
  label: string;
  value: DateParts | null;
  onSave: (v: DateParts | null) => Promise<void>;
  placeholder?: string;
  hint?: ReactNode;
  requireDay?: boolean;
  requireYear?: boolean;
  onDraftChange?: (draft: DateDraft | null) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [month, setMonth] = useState(value?.month ?? null);
  const [day, setDay] = useState(value?.day ?? null);
  const [year, setYear] = useState(value?.year ?? null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function startEditing() {
    const nextMonth = value?.month ?? null;
    const nextDay = value?.day ?? null;
    const nextYear = value?.year ?? null;
    setMonth(nextMonth);
    setDay(nextDay);
    setYear(nextYear);
    setError(null);
    setEditing(true);
    onDraftChange?.({ month: nextMonth, day: nextDay, year: nextYear });
  }

  async function save(next: DateParts | null) {
    setSaving(true);
    setError(null);
    try {
      await onSave(next);
      setEditing(false);
      onDraftChange?.(null);
    } catch (err) {
      setError(extractApiErrorOr(err, "couldn't save — try again"));
    } finally {
      setSaving(false);
    }
  }

  const yearOptions = requireYear ? YEARS : OPTIONAL_YEAR_OPTIONS;

  if (!editing) {
    return (
      <div className="flex items-center justify-between">
        <div>
          <div className="text-muted text-xs">{label}</div>
          <div className="text-foreground text-sm">
            {value ? displayValue(value, requireDay, requireYear) : placeholder}
          </div>
        </div>
        <Button variant="ghost" onClick={startEditing} aria-label={`edit ${label}`}>
          edit
        </Button>
      </div>
    );
  }

  const canSave =
    month !== null && (!requireDay || day !== null) && (!requireYear || year !== null);

  return (
    <div className="flex flex-col gap-2">
      <div className="text-muted text-xs">{label}</div>
      <div className="grid grid-cols-3 gap-2">
        <Select
          label="month"
          options={MONTH_OPTIONS}
          value={month ? String(month) : ''}
          placeholder="month"
          onChange={(e) => {
            const nextMonth = e.target.value ? Number(e.target.value) : null;
            const nextDay = nextMonth && day && day > daysInMonth(nextMonth, year) ? null : day;
            setMonth(nextMonth);
            if (nextDay !== day) setDay(nextDay);
            if (error) setError(null);
            onDraftChange?.({ month: nextMonth, day: nextDay, year });
          }}
        />
        <Select
          label="day"
          options={dayOptions(month, year)}
          value={day ? String(day) : ''}
          placeholder="day"
          onChange={(e) => {
            const nextDay = e.target.value ? Number(e.target.value) : null;
            setDay(nextDay);
            if (error) setError(null);
            onDraftChange?.({ month, day: nextDay, year });
          }}
        />
        <Select
          label="year"
          options={yearOptions}
          value={year ? String(year) : ''}
          placeholder="year"
          onChange={(e) => {
            const nextYear = e.target.value ? Number(e.target.value) : null;
            const nextDay = month && day && day > daysInMonth(month, nextYear) ? null : day;
            setYear(nextYear);
            if (nextDay !== day) setDay(nextDay);
            if (error) setError(null);
            onDraftChange?.({ month, day: nextDay, year: nextYear });
          }}
        />
      </div>
      {hint ? <p className="text-foreground-tertiary text-xs">{hint}</p> : null}
      {error ? <p className="text-destructive text-xs">{error}</p> : null}
      <div className="flex items-center justify-end gap-2">
        {value ? (
          <Button variant="ghost" onClick={() => void save(null)} disabled={saving}>
            clear
          </Button>
        ) : null}
        <Button
          variant="ghost"
          onClick={() => {
            setError(null);
            setEditing(false);
            onDraftChange?.(null);
          }}
          disabled={saving}
        >
          cancel
        </Button>
        <Button
          onClick={() => {
            if (month == null) return;
            void save({ month, day, year });
          }}
          disabled={saving || !canSave}
        >
          save
        </Button>
      </div>
    </div>
  );
}

export function InlineVeganniversary({
  value,
  onSave,
  onDraftChange,
}: {
  value: DateParts | null;
  onSave: (v: Veganniversary | null) => Promise<void>;
  onDraftChange?: (draft: DateDraft | null) => void;
}) {
  return (
    <InlineBirthday
      label="veganniversary"
      value={value}
      onSave={(v) => onSave(v?.year != null ? { month: v.month, day: v.day, year: v.year } : null)}
      placeholder="add your veganniversary"
      requireDay={false}
      requireYear
      hint={VEGANNIVERSARY_HINT}
      {...(onDraftChange ? { onDraftChange } : {})}
    />
  );
}
