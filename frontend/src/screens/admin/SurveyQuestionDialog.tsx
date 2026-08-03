import type { SyntheticEvent } from 'react';
import { useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import {
  type SurveyQuestion,
  type SurveyQuestionInput,
  type SurveyQuestionType,
  useCreateSurveyQuestion,
  useUpdateSurveyQuestion,
} from '@/api/surveyAdmin';
import { DEFAULT_SURVEY_QUESTION_TYPE } from '@/api/surveys';
import {
  QUESTION_TYPE_OPTIONS,
  questionOptionsError,
  questionTypeWantsOptions,
} from '@/components/questions/questionTypeOptions';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { TextField } from '@/components/ui/TextField';

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
    () => existing?.fieldType ?? DEFAULT_SURVEY_QUESTION_TYPE,
  );
  const [required, setRequired] = useState(() => existing?.required ?? false);
  const [optionsText, setOptionsText] = useState(() => existing?.options.join('\n') ?? '');
  const [error, setError] = useState<string | null>(null);

  const wantsOptions = questionTypeWantsOptions(fieldType);
  const busy = create.isPending || update.isPending;

  async function submit(e: SyntheticEvent) {
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
    const optionsError = questionOptionsError(wantsOptions, options);
    if (optionsError) {
      setError(optionsError);
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
          options={QUESTION_TYPE_OPTIONS.map((t) => ({ value: t.value, label: t.label }))}
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
  return extractApiErrorOr(err, "couldn't save — try again");
}
