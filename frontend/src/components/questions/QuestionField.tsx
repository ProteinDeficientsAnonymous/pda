import { QuestionType } from '@/api/questionTypes';
import type { AnswerValue, SurveyQuestion } from '@/api/surveys';
import { LabelSuffix } from '@/components/ui/LabelSuffix';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { TextField } from '@/components/ui/TextField';
import { cn } from '@/utils/cn';

import { checkboxValues } from './checkboxAnswer';
import { FieldError } from './FieldError';
import { formatPollOption } from './pollOption';
import { ScaleRating } from './ScaleRating';
import { SectionHeader } from './SectionHeader';
import { StarRating } from './StarRating';

interface Props {
  question: Pick<SurveyQuestion, 'label' | 'fieldType' | 'options' | 'required' | 'description'>;
  value: AnswerValue | undefined;
  onChange: (v: AnswerValue) => void;
  error?: string | undefined;
  readOnly?: boolean;
}

/** Shared answer field for surveys and join form questions. */
export function QuestionField({ question, value, onChange, error, readOnly }: Props) {
  const { label } = question;
  const labelSuffix = question.required ? '· required' : undefined;
  const common = { label, labelSuffix, error, disabled: readOnly };

  switch (question.fieldType) {
    case QuestionType.Textarea:
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
    case QuestionType.Number:
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
    case QuestionType.Radio:
      return (
        <RadioGroup
          {...common}
          options={question.options}
          value={asString(value)}
          onChange={onChange}
        />
      );
    case QuestionType.Select:
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
    case QuestionType.Checkbox:
      return (
        <CheckboxGroup
          {...common}
          options={question.options}
          value={checkboxValues(value)}
          onChange={onChange}
        />
      );
    case QuestionType.Boolean:
      return (
        <RadioGroup
          {...common}
          options={['yes', 'no']}
          value={asString(value)}
          onChange={onChange}
        />
      );
    case QuestionType.Stars:
      return (
        <StarRating
          label={label}
          labelSuffix={labelSuffix}
          error={error}
          value={Number(asString(value)) || 0}
          labels={question.options}
          readOnly={readOnly}
          onChange={(n) => {
            onChange(String(n));
          }}
        />
      );
    case QuestionType.Scale:
      return (
        <ScaleRating
          label={label}
          labelSuffix={labelSuffix}
          error={error}
          value={Number(asString(value)) || 0}
          readOnly={readOnly}
          onChange={(n) => {
            onChange(String(n));
          }}
        />
      );
    case QuestionType.DatetimePoll:
      return (
        <DatetimePoll
          {...common}
          options={question.options}
          value={asAvailabilityMap(value)}
          onChange={onChange}
        />
      );
    case QuestionType.Section:
      return <SectionHeader label={label} description={question.description} />;
    case QuestionType.Text:
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
function asAvailabilityMap(v: AnswerValue | undefined): Record<string, string> {
  return typeof v === 'object' && !Array.isArray(v) ? v : {};
}

function RadioGroup({
  label,
  labelSuffix,
  options,
  value,
  onChange,
  error,
  disabled,
}: {
  label: string;
  labelSuffix: string | undefined;
  options: string[];
  value: string;
  onChange: (v: string) => void;
  error?: string | undefined;
  disabled?: boolean | undefined;
}) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-foreground text-sm font-medium">
        {label}
        {labelSuffix ? <LabelSuffix>{labelSuffix}</LabelSuffix> : null}
      </legend>
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
      <FieldError error={error} />
    </fieldset>
  );
}

function CheckboxGroup({
  label,
  labelSuffix,
  options,
  value,
  onChange,
  error,
  disabled,
}: {
  label: string;
  labelSuffix: string | undefined;
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
      <legend className="text-foreground text-sm font-medium">
        {label}
        {labelSuffix ? <LabelSuffix>{labelSuffix}</LabelSuffix> : null}
      </legend>
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
      <FieldError error={error} />
    </fieldset>
  );
}

function DatetimePoll({
  label,
  labelSuffix,
  options,
  value,
  onChange,
  error,
  disabled,
}: {
  label: string;
  labelSuffix: string | undefined;
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
      <legend className="text-foreground text-sm font-medium">
        {label}
        {labelSuffix ? <LabelSuffix>{labelSuffix}</LabelSuffix> : null}
      </legend>
      {options.map((option) => {
        const current = value[option];
        return (
          <div
            key={option}
            className="border-border bg-surface flex flex-wrap items-center justify-between gap-2 rounded-md border px-3 py-2"
          >
            <span className="text-sm">{formatPollOption(option)}</span>
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
      <FieldError error={error} />
    </fieldset>
  );
}
