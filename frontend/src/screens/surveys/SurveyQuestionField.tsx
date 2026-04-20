// Renders one survey question by type. Returns the answer as the exact
// shape the backend expects (strings for most, dict for datetime_poll).

import type { SurveyQuestion, AnswerValue } from '@/api/surveys';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { Textarea } from '@/components/ui/Textarea';
import { cn } from '@/utils/cn';

interface Props {
  question: SurveyQuestion;
  value: AnswerValue | undefined;
  onChange: (v: AnswerValue) => void;
  error?: string | undefined;
  readOnly?: boolean;
}

export function SurveyQuestionField({ question, value, onChange, error, readOnly }: Props) {
  const label = question.required ? question.label : `${question.label} (optional)`;
  const common = { label, error, disabled: readOnly };

  switch (question.fieldType) {
    case 'textarea':
      return (
        <Textarea
          {...common}
          value={asString(value)}
          onChange={(e) => {
            onChange(e.target.value);
          }}
          rows={5}
          maxLength={2000}
        />
      );
    case 'number':
      return (
        <TextField
          {...common}
          type="number"
          value={asString(value)}
          onChange={(e) => {
            onChange(e.target.value);
          }}
        />
      );
    case 'select':
      return (
        <RadioGroup
          {...common}
          options={question.options}
          value={asString(value)}
          onChange={onChange}
        />
      );
    case 'dropdown':
      return (
        <Select
          {...common}
          value={asString(value)}
          onChange={(e) => {
            onChange(e.target.value);
          }}
          options={question.options.map((o) => ({ value: o, label: o }))}
          placeholder="select one"
        />
      );
    case 'multiselect':
      return (
        <CheckboxGroup
          {...common}
          options={question.options}
          value={asCsv(value)}
          onChange={(list) => {
            onChange(list.join(','));
          }}
        />
      );
    case 'yes_no':
      return (
        <RadioGroup
          {...common}
          options={['yes', 'no']}
          value={asString(value)}
          onChange={onChange}
        />
      );
    case 'rating':
      return (
        <StarRating
          label={label}
          error={error}
          value={Number(asString(value)) || 0}
          labels={question.options}
          readOnly={readOnly}
          onChange={(n) => {
            onChange(String(n));
          }}
        />
      );
    case 'datetime_poll':
      return (
        <DatetimePoll
          {...common}
          options={question.options}
          value={asAvailabilityMap(value)}
          onChange={onChange}
        />
      );
    case 'text':
    default:
      return (
        <TextField
          {...common}
          value={asString(value)}
          onChange={(e) => {
            onChange(e.target.value);
          }}
          maxLength={2000}
        />
      );
  }
}

function asString(v: AnswerValue | undefined): string {
  return typeof v === 'string' ? v : '';
}
function asCsv(v: AnswerValue | undefined): string[] {
  const s = asString(v);
  return s ? s.split(',').filter(Boolean) : [];
}
function asAvailabilityMap(v: AnswerValue | undefined): Record<string, string> {
  return typeof v === 'object' ? v : {};
}

function RadioGroup({
  label,
  options,
  value,
  onChange,
  error,
  disabled,
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (v: string) => void;
  error?: string | undefined;
  disabled?: boolean | undefined;
}) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-foreground text-sm font-medium">{label}</legend>
      {options.map((o) => (
        <label key={o} className="flex items-center gap-2 text-sm">
          <input
            type="radio"
            name={label}
            value={o}
            checked={value === o}
            disabled={disabled}
            onChange={() => {
              onChange(o);
            }}
          />
          <span>{o}</span>
        </label>
      ))}
      {error ? (
        <p role="alert" className="text-xs text-red-600">
          {error}
        </p>
      ) : null}
    </fieldset>
  );
}

function CheckboxGroup({
  label,
  options,
  value,
  onChange,
  error,
  disabled,
}: {
  label: string;
  options: string[];
  value: string[];
  onChange: (v: string[]) => void;
  error?: string | undefined;
  disabled?: boolean | undefined;
}) {
  function toggle(o: string) {
    if (value.includes(o)) onChange(value.filter((v) => v !== o));
    else onChange([...value, o]);
  }
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-foreground text-sm font-medium">{label}</legend>
      {options.map((o) => (
        <label key={o} className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={value.includes(o)}
            disabled={disabled}
            onChange={() => {
              toggle(o);
            }}
          />
          <span>{o}</span>
        </label>
      ))}
      {error ? (
        <p role="alert" className="text-xs text-red-600">
          {error}
        </p>
      ) : null}
    </fieldset>
  );
}

function StarRating({
  label,
  value,
  labels,
  onChange,
  error,
  readOnly,
}: {
  label: string;
  value: number;
  labels: string[];
  onChange: (n: number) => void;
  error?: string | undefined;
  readOnly?: boolean | undefined;
}) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-foreground text-sm font-medium">{label}</legend>
      <div role="radiogroup" aria-label={label} className="flex gap-1">
        {[1, 2, 3, 4, 5].map((n) => {
          const filled = n <= value;
          return (
            <button
              key={n}
              type="button"
              role="radio"
              aria-checked={n === value}
              aria-label={labels[n - 1] ?? `${String(n)} star${n === 1 ? '' : 's'}`}
              disabled={readOnly}
              onClick={() => {
                onChange(n);
              }}
              className={cn(
                'text-2xl transition-colors disabled:cursor-not-allowed',
                filled ? 'text-amber-500' : 'text-toggle-off',
              )}
            >
              ★
            </button>
          );
        })}
      </div>
      {error ? (
        <p role="alert" className="text-xs text-red-600">
          {error}
        </p>
      ) : null}
    </fieldset>
  );
}

function DatetimePoll({
  label,
  options,
  value,
  onChange,
  error,
  disabled,
}: {
  label: string;
  options: string[];
  value: Record<string, string>;
  onChange: (v: Record<string, string>) => void;
  error?: string | undefined;
  disabled?: boolean | undefined;
}) {
  function pick(option: string, availability: 'yes' | 'maybe') {
    if (value[option] === availability) {
      const { [option]: _removed, ...rest } = value;
      onChange(rest);
    } else {
      onChange({ ...value, [option]: availability });
    }
  }
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="text-foreground text-sm font-medium">{label}</legend>
      {options.map((option) => {
        const current = value[option];
        return (
          <div
            key={option}
            className="border-border bg-surface flex flex-wrap items-center justify-between gap-2 rounded-md border px-3 py-2"
          >
            <span className="text-sm">{new Date(option).toLocaleString()}</span>
            <div className="flex gap-1" role="radiogroup">
              {(['yes', 'maybe'] as const).map((a) => (
                <button
                  key={a}
                  type="button"
                  role="radio"
                  aria-checked={current === a}
                  disabled={disabled}
                  onClick={() => {
                    pick(option, a);
                  }}
                  className={cn(
                    'rounded-full px-3 py-1 text-xs transition-colors',
                    current === a
                      ? 'bg-brand-600 text-brand-on'
                      : 'bg-surface-dim text-foreground-secondary hover:bg-surface-raised',
                  )}
                >
                  {a}
                </button>
              ))}
            </div>
          </div>
        );
      })}
      {error ? (
        <p role="alert" className="text-xs text-red-600">
          {error}
        </p>
      ) : null}
    </fieldset>
  );
}
