import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';

import type { RsvpAnswerValue, RsvpQuestionDraft } from './rsvpQuestions';

interface Props {
  questions: readonly RsvpQuestionDraft[];
  answers: Readonly<Record<string, RsvpAnswerValue | undefined>>;
  onChange: (questionId: string, value: RsvpAnswerValue) => void;
  errors: Readonly<Record<string, string | undefined>>;
  disabled?: boolean;
}

export function RsvpQuestionFields({
  questions,
  answers,
  onChange,
  errors,
  disabled = false,
}: Props) {
  if (questions.length === 0) return null;

  return (
    <div className="flex flex-col gap-4">
      {questions.map((question) => (
        <QuestionField
          key={question.id}
          question={question}
          value={answers[question.id]}
          onChange={(value) => {
            onChange(question.id, value);
          }}
          error={errors[question.id]}
          disabled={disabled}
        />
      ))}
    </div>
  );
}

function QuestionField({
  question,
  value,
  onChange,
  error,
  disabled,
}: {
  question: RsvpQuestionDraft;
  value: RsvpAnswerValue | undefined;
  onChange: (value: RsvpAnswerValue) => void;
  error?: string | undefined;
  disabled: boolean;
}) {
  const label = question.required ? question.label : `${question.label} (optional)`;

  if (question.fieldType === 'free_response') {
    return (
      <Textarea
        label={label}
        value={typeof value === 'string' ? value : ''}
        onChange={(e) => {
          onChange(e.target.value);
        }}
        error={error}
        disabled={disabled}
        rows={3}
        maxLength={2000}
      />
    );
  }

  if (question.fieldType === 'select_one') {
    return (
      <Select
        label={label}
        value={typeof value === 'string' ? value : ''}
        onChange={(e) => {
          onChange(e.target.value);
        }}
        options={question.options.map((o) => ({ value: o, label: o }))}
        placeholder="choose one"
        error={error}
        disabled={disabled}
      />
    );
  }

  const selected = Array.isArray(value) ? value : [];
  return (
    <CheckboxGroup
      label={label}
      options={question.options}
      value={selected}
      onChange={onChange}
      error={error}
      disabled={disabled}
    />
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
  disabled: boolean;
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
        <p role="alert" className="text-destructive text-xs">
          {error}
        </p>
      ) : null}
    </fieldset>
  );
}
