import type { SyntheticEvent } from 'react';
import { useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import type { JoinQuestion, JoinQuestionInput, JoinQuestionType } from '@/api/join';
import { useCreateJoinQuestion, useUpdateJoinQuestion } from '@/api/join';
import {
  DEFAULT_JOIN_QUESTION_TYPE,
  JOIN_QUESTION_TYPE_OPTIONS,
  questionTypeWantsOptions,
} from '@/components/questions/questionTypeOptions';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { TextField } from '@/components/ui/TextField';

interface Props {
  open: boolean;
  onClose: () => void;
  /** If set, the dialog is in edit mode. */
  existing?: JoinQuestion | undefined;
}

export function JoinQuestionDialog(props: Props) {
  if (!props.open) return null;
  return <JoinQuestionDialogBody key={props.existing?.id ?? 'new'} {...props} />;
}

function JoinQuestionDialogBody({ open, onClose, existing }: Props) {
  const create = useCreateJoinQuestion();
  const update = useUpdateJoinQuestion(existing?.id ?? '');

  const [label, setLabel] = useState(() => existing?.label ?? '');
  const [fieldType, setFieldType] = useState<JoinQuestionType>(
    () => existing?.fieldType ?? DEFAULT_JOIN_QUESTION_TYPE,
  );
  const [required, setRequired] = useState(() => existing?.required ?? false);
  const [optionsText, setOptionsText] = useState(() => existing?.options.join('\n') ?? '');
  const [error, setError] = useState<string | null>(null);

  const busy = create.isPending || update.isPending;
  const wantsOptions = questionTypeWantsOptions(fieldType);

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setError(null);
    if (!label.trim()) {
      setError('label required');
      return;
    }
    const options = wantsOptions
      ? optionsText
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean)
      : [];
    if (wantsOptions && options.length === 0) {
      setError('add at least one option for a dropdown question');
      return;
    }
    const input: JoinQuestionInput = {
      label: label.trim(),
      fieldType,
      options,
      required,
    };
    try {
      if (existing) await update.mutateAsync(input);
      else await create.mutateAsync(input);
      onClose();
    } catch (err) {
      setError(extractError(err));
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title={existing ? 'edit question' : 'add question'}>
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
            setFieldType(e.target.value as JoinQuestionType);
          }}
          options={JOIN_QUESTION_TYPE_OPTIONS}
        />
        {wantsOptions ? (
          <Textarea
            label="options"
            value={optionsText}
            onChange={(e) => {
              setOptionsText(e.target.value);
            }}
            hint="one per line"
            rows={5}
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

function extractError(err: unknown): string {
  return extractApiErrorOr(err, "couldn't save — try again");
}
