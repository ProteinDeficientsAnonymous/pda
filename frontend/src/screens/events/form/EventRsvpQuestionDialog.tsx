import type { SyntheticEvent } from 'react';
import { useState } from 'react';

import { DEFAULT_RSVP_QUESTION_TYPE } from '@/api/eventRsvpQuestions';
import { QuestionType } from '@/api/questionTypes';
import { QuestionOptionsEditor } from '@/components/questions/QuestionOptionsEditor';
import {
  normalizeQuestionOptions,
  questionOptionsError,
} from '@/components/questions/questionTypeOptions';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';

import {
  newQuestionId,
  RSVP_QUESTION_TYPE_OPTIONS,
  type RsvpQuestionDraft,
  type RsvpQuestionType,
  wantsOptions,
} from '../rsvpQuestions';

const MAX_OPTION_LENGTH = 200;

interface Props {
  open: boolean;
  onClose: () => void;
  onSave: (question: RsvpQuestionDraft) => void;
  existing?: RsvpQuestionDraft | undefined;
}

export function EventRsvpQuestionDialog(props: Props) {
  if (!props.open) return null;
  return <EventRsvpQuestionDialogBody key={props.existing?.id ?? 'new'} {...props} />;
}

function EventRsvpQuestionDialogBody({ open, onClose, onSave, existing }: Props) {
  const [label, setLabel] = useState(() => existing?.label ?? '');
  const [fieldType, setFieldType] = useState<RsvpQuestionType>(
    () => existing?.fieldType ?? DEFAULT_RSVP_QUESTION_TYPE,
  );
  const [required, setRequired] = useState(() => existing?.required ?? false);
  const [options, setOptions] = useState<string[]>(() =>
    existing?.options.length ? [...existing.options] : [''],
  );
  const [error, setError] = useState<string | null>(null);

  function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    e.stopPropagation();
    setError(null);
    if (!label.trim()) {
      setError('question required');
      return;
    }
    const needsOptions = wantsOptions(fieldType);
    const normalized = needsOptions ? normalizeQuestionOptions(options) : [];
    const optionsError = questionOptionsError(needsOptions, normalized);
    if (optionsError) {
      setError(optionsError);
      return;
    }
    if (normalized.some((option) => option.length > MAX_OPTION_LENGTH)) {
      setError(`options must be ${String(MAX_OPTION_LENGTH)} characters or fewer`);
      return;
    }
    if (fieldType === QuestionType.Checkbox && normalized.some((option) => option.includes(','))) {
      setError('options cannot contain commas');
      return;
    }
    onSave({
      id: existing?.id ?? newQuestionId(),
      label: label.trim(),
      fieldType,
      options: normalized,
      required,
    });
    onClose();
  }

  return (
    <Dialog open={open} onClose={onClose} title={existing ? 'edit question' : 'add question'}>
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <TextField
          label="question"
          value={label}
          onChange={(e) => {
            setLabel(e.target.value);
          }}
          maxLength={200}
        />
        <Select
          label="type"
          value={fieldType}
          onChange={(e) => {
            const next = e.target.value as RsvpQuestionType;
            setFieldType(next);
            if (wantsOptions(next) && options.every((option) => !option.trim())) {
              setOptions(['']);
            }
          }}
          options={RSVP_QUESTION_TYPE_OPTIONS.map((o) => ({
            value: o.value,
            label: o.label,
          }))}
        />
        {wantsOptions(fieldType) ? (
          <QuestionOptionsEditor
            options={options}
            onChange={setOptions}
            maxLength={MAX_OPTION_LENGTH}
          />
        ) : null}
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={required}
            onChange={(e) => {
              setRequired(e.target.checked);
            }}
          />
          <span>required</span>
        </label>
        {error ? (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        ) : null}
        <div className="mt-2 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose} type="button">
            cancel
          </Button>
          <Button type="submit">save</Button>
        </div>
      </form>
    </Dialog>
  );
}
