import { getDaysInMonth } from 'date-fns';
import { type ReactNode, useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Toggle } from '@/components/ui/Toggle';
import { formatBirthday, formatVeganversary } from '@/utils/datetime';

export interface DateParts {
  month: number;
  day: number | null;
  year: number | null;
}

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

function dayOptions(month: number | null) {
  const count = month ? getDaysInMonth(new Date(2000, month - 1)) : 31;
  return Array.from({ length: count }, (_, i) => ({ value: String(i + 1), label: String(i + 1) }));
}

function displayValue(value: DateParts, requireDay: boolean, requireYear: boolean): string {
  if (requireYear && value.year != null) {
    return formatVeganversary({ month: value.month, day: value.day, year: value.year });
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
  privacy,
}: {
  label: string;
  value: DateParts | null;
  onSave: (v: DateParts | null) => Promise<void>;
  placeholder?: string;
  hint?: ReactNode;
  requireDay?: boolean;
  requireYear?: boolean;
  privacy?: {
    showOnProfile: boolean;
    onShowOnProfileChange: (v: boolean) => void;
    optOutShoutout: boolean;
    onOptOutShoutoutChange: (v: boolean) => void;
  };
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

  async function save(next: DateParts | null) {
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

  const yearOptions = requireYear ? YEARS : OPTIONAL_YEAR_OPTIONS;

  if (!editing) {
    return (
      <div className="flex flex-col gap-1">
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
        {hint ? <p className="text-foreground-tertiary text-xs">{hint}</p> : null}
      </div>
    );
  }

  const canSave =
    month !== null && (!requireDay || day !== null) && (!requireYear || year !== null);

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
          options={yearOptions}
          value={year ? String(year) : ''}
          placeholder="year"
          onChange={(e) => {
            setYear(e.target.value ? Number(e.target.value) : null);
            if (error) setError(null);
          }}
        />
      </div>
      {hint ? <p className="text-foreground-tertiary text-xs">{hint}</p> : null}
      {privacy ? <VeganversaryPrivacy privacy={privacy} /> : null}
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

function VeganversaryPrivacy({
  privacy,
}: {
  privacy: {
    showOnProfile: boolean;
    onShowOnProfileChange: (v: boolean) => void;
    optOutShoutout: boolean;
    onOptOutShoutoutChange: (v: boolean) => void;
  };
}) {
  return (
    <div className="flex flex-col gap-1">
      <Toggle
        label="display on my profile"
        checked={privacy.showOnProfile}
        onChange={privacy.onShowOnProfileChange}
      />
      <Toggle
        label="don't celebrate me by name"
        checked={privacy.optOutShoutout}
        onChange={privacy.onOptOutShoutoutChange}
      />
    </div>
  );
}
