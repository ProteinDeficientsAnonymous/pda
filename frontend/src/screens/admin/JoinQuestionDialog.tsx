// Create / edit a single JoinFormQuestion. Kept in its own file so the
// parent screen stays focused on list semantics + reorder.

import { useState } from 'react';
import { isAxiosError } from 'axios';
import type { JoinQuestion, JoinQuestionInput, JoinQuestionType } from '@/api/join';
import { useCreateJoinQuestion, useUpdateJoinQuestion } from '@/api/join';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { Textarea } from '@/components/ui/Textarea';

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
  const [fieldType, setFieldType] = useState<JoinQuestionType>(() => existing?.fieldType ?? 'text');
  const [required, setRequired] = useState(() => existing?.required ?? false);
  const [optionsText, setOptionsText] = useState(() => existing?.options.join('\n') ?? '');
  const [error, setError] = useState<string | null>(null);

  const busy = create.isPending || update.isPending;

  async function onSubmit(e: React.SyntheticEvent) {
    e.preventDefault();
    setError(null);
    if (!label.trim()) {
      setError('label required');
      return;
    }
    const options =
      fieldType === 'select'
        ? optionsText
            .split('\n')
            .map((s) => s.trim())
            .filter(Boolean)
        : [];
    if (fieldType === 'select' && options.length === 0) {
      setError('add at least one option for a select question');
      return;
    }
    const input: JoinQuestionInput = { label: label.trim(), fieldType, options, required };
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
          options={[
            { value: 'text', label: 'text' },
            { value: 'select', label: 'select (one of)' },
          ]}
        />
        {fieldType === 'select' ? (
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
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't save — try again";
}
