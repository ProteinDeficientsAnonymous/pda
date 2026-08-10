import type { SyntheticEvent } from 'react';
import { useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import type { QuestionType } from '@/api/questionTypes';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';

import { normalizeQuestionOptions, QuestionOptionsEditor } from './QuestionOptionsEditor';
import { questionOptionsError, questionTypeWantsOptions } from './questionTypeOptions';

export interface QuestionAuthorValues<T extends string = QuestionType> {
  label: string;
  fieldType: T;
  options: string[];
  required: boolean;
}

interface TypeOption<T extends string> {
  value: T;
  label: string;
}

interface Props<T extends string> {
  open: boolean;
  onClose: () => void;
  title: string;
  initial: QuestionAuthorValues<T>;
  typeOptions: TypeOption<T>[];
  optionsHint?: string | ((fieldType: T) => string | undefined);
  busy: boolean;
  onSave: (values: QuestionAuthorValues<T>) => Promise<void>;
  errorFallback?: string;
}

export function QuestionAuthorDialog<T extends string>(props: Props<T>) {
  if (!props.open) return null;
  return <QuestionAuthorDialogBody {...props} />;
}

function QuestionAuthorDialogBody<T extends string>({
  open,
  onClose,
  title,
  initial,
  typeOptions,
  optionsHint,
  busy,
  onSave,
  errorFallback = "couldn't save — try again",
}: Props<T>) {
  const [label, setLabel] = useState(() => initial.label);
  const [fieldType, setFieldType] = useState<T>(() => initial.fieldType);
  const [required, setRequired] = useState(() => initial.required);
  const [options, setOptions] = useState<string[]>(() =>
    initial.options.length > 0 ? [...initial.options] : [''],
  );
  const [error, setError] = useState<string | null>(null);

  const wantsOptions = questionTypeWantsOptions(fieldType as QuestionType);
  const hint = typeof optionsHint === 'function' ? optionsHint(fieldType) : optionsHint;

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setError(null);
    if (!label.trim()) {
      setError('label required');
      return;
    }
    const normalized = wantsOptions ? normalizeQuestionOptions(options) : [];
    const optionsError = questionOptionsError(wantsOptions, normalized);
    if (optionsError) {
      setError(optionsError);
      return;
    }
    try {
      await onSave({
        label: label.trim(),
        fieldType,
        options: normalized,
        required,
      });
      onClose();
    } catch (err) {
      setError(extractApiErrorOr(err, errorFallback));
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title={title}>
      <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3">
        <TextField
          label="label"
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
            const next = e.target.value as T;
            setFieldType(next);
            if (questionTypeWantsOptions(next as QuestionType) && options.every((o) => !o.trim())) {
              setOptions(['']);
            }
          }}
          options={typeOptions}
        />
        {wantsOptions ? (
          <QuestionOptionsEditor options={options} onChange={setOptions} hint={hint} />
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
          <Button variant="ghost" onClick={onClose} disabled={busy} type="button">
            cancel
          </Button>
          <Button type="submit" disabled={busy}>
            {busy ? 'saving…' : 'save'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
