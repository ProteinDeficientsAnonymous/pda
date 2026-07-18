import { getDaysInMonth } from 'date-fns';
import { useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import type { Birthday } from '@/models/user';
import { formatBirthday } from '@/utils/datetime';

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
const YEAR_OPTIONS = [
  { value: NO_YEAR, label: 'prefer not to say' },
  ...Array.from({ length: 120 }, (_, i) => {
    const year = CURRENT_YEAR - i;
    return { value: String(year), label: String(year) };
  }),
];

function dayOptions(month: number | null) {
  const count = month ? getDaysInMonth(new Date(2000, month - 1)) : 31;
  return Array.from({ length: count }, (_, i) => ({ value: String(i + 1), label: String(i + 1) }));
}

export function InlineBirthday({
  label,
  value,
  onSave,
  placeholder,
}: {
  label: string;
  value: Birthday | null;
  onSave: (v: Birthday | null) => Promise<void>;
  placeholder?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [month, setMonth] = useState(value?.month ?? null);
  const [day, setDay] = useState(value?.day ?? null);
  const [year, setYear] = useState(value?.year ?? null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function startEditing() {
    setMonth(value?.month ?? null);
    setDay(value?.day ?? null);
    setYear(value?.year ?? null);
    setError(null);
    setEditing(true);
  }

  async function save(next: Birthday | null) {
    setSaving(true);
    setError(null);
    try {
      await onSave(next);
      setEditing(false);
    } catch (err) {
      setError(extractApiErrorOr(err, "couldn't save — try again"));
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <div className="flex items-center justify-between">
        <div>
          <div className="text-muted text-xs">{label}</div>
          <div className="text-foreground text-sm">
            {value ? formatBirthday(value) : placeholder}
          </div>
        </div>
        <Button variant="ghost" onClick={startEditing} aria-label={`edit ${label}`}>
          edit
        </Button>
      </div>
    );
  }

  const canSave = month !== null && day !== null;

  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-3 gap-2">
        <Select
          label="month"
          options={MONTH_OPTIONS}
          value={month ? String(month) : ''}
          placeholder="month"
          onChange={(e) => {
            const nextMonth = e.target.value ? Number(e.target.value) : null;
            setMonth(nextMonth);
            if (nextMonth && day && day > getDaysInMonth(new Date(2000, nextMonth - 1))) {
              setDay(null);
            }
            if (error) setError(null);
          }}
        />
        <Select
          label="day"
          options={dayOptions(month)}
          value={day ? String(day) : ''}
          placeholder="day"
          onChange={(e) => {
            setDay(e.target.value ? Number(e.target.value) : null);
            if (error) setError(null);
          }}
        />
        <Select
          label="year"
          options={YEAR_OPTIONS}
          value={year ? String(year) : NO_YEAR}
          onChange={(e) => {
            setYear(e.target.value ? Number(e.target.value) : null);
            if (error) setError(null);
          }}
        />
      </div>
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
          }}
          disabled={saving}
        >
          cancel
        </Button>
        <Button
          onClick={() => {
            if (canSave) void save({ month, day, year });
          }}
          disabled={saving || !canSave}
        >
          save
        </Button>
      </div>
    </div>
  );
}
