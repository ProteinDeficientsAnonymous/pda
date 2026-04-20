// Create / edit a single survey question. Covers all 9 field types; options
// textarea appears only for types that use them.

import { useState } from 'react';
import { isAxiosError } from 'axios';
import {
  useCreateSurveyQuestion,
  useUpdateSurveyQuestion,
  type SurveyQuestion,
  type SurveyQuestionInput,
  type SurveyQuestionType,
} from '@/api/surveyAdmin';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { Textarea } from '@/components/ui/Textarea';

const TYPES: { value: SurveyQuestionType; label: string; wantsOptions: boolean }[] = [
  { value: 'text', label: 'short text', wantsOptions: false },
  { value: 'textarea', label: 'long text', wantsOptions: false },
  { value: 'number', label: 'number', wantsOptions: false },
  { value: 'select', label: 'single choice (radio)', wantsOptions: true },
  { value: 'dropdown', label: 'dropdown', wantsOptions: true },
  { value: 'multiselect', label: 'multiple choice', wantsOptions: true },
  { value: 'yes_no', label: 'yes / no', wantsOptions: false },
  { value: 'rating', label: '1–5 rating', wantsOptions: true },
  { value: 'datetime_poll', label: 'datetime poll (iso options)', wantsOptions: true },
];

interface Props {
  surveyId: string;
  open: boolean;
  onClose: () => void;
  existing?: SurveyQuestion | undefined;
}

export function SurveyQuestionDialog(props: Props) {
  if (!props.open) return null;
  // Dialog body lives in a sibling component keyed by `existing.id` so each
  // edit session gets fresh state via remount (avoids setState-in-effect).
  return <SurveyQuestionDialogBody key={props.existing?.id ?? 'new'} {...props} />;
}

function SurveyQuestionDialogBody({ surveyId, open, onClose, existing }: Props) {
  const create = useCreateSurveyQuestion(surveyId);
  const update = useUpdateSurveyQuestion(surveyId, existing?.id ?? '');

  const [label, setLabel] = useState(() => existing?.label ?? '');
  const [fieldType, setFieldType] = useState<SurveyQuestionType>(
    () => existing?.fieldType ?? 'text',
  );
  const [required, setRequired] = useState(() => existing?.required ?? false);
  const [optionsText, setOptionsText] = useState(() => existing?.options.join('\n') ?? '');
  const [error, setError] = useState<string | null>(null);

  const wantsOptions = TYPES.find((t) => t.value === fieldType)?.wantsOptions ?? false;
  const busy = create.isPending || update.isPending;

  async function submit(e: React.SyntheticEvent) {
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
      setError('add at least one option');
      return;
    }
    const input: SurveyQuestionInput = {
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

  const optionsHint =
    fieldType === 'rating'
      ? 'one label per star (up to 5)'
      : fieldType === 'datetime_poll'
        ? 'one ISO-8601 datetime per line'
        : 'one option per line';

  return (
    <Dialog open={open} onClose={onClose} title={existing ? 'edit question' : 'add question'}>
      <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-3">
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
            setFieldType(e.target.value as SurveyQuestionType);
          }}
          options={TYPES.map((t) => ({ value: t.value, label: t.label }))}
        />
        {wantsOptions ? (
          <Textarea
            label="options"
            value={optionsText}
            onChange={(e) => {
              setOptionsText(e.target.value);
            }}
            hint={optionsHint}
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
