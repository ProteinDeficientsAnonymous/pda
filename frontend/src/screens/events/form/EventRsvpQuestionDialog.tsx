import type { SyntheticEvent } from 'react';
import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { TextField } from '@/components/ui/TextField';

import {
  newQuestionId,
  parseOptionsText,
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
    () => existing?.fieldType ?? 'textarea',
  );
  const [required, setRequired] = useState(() => existing?.required ?? false);
  const [optionsText, setOptionsText] = useState(() => existing?.options.join('\n') ?? '');
  const [error, setError] = useState<string | null>(null);

  function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    e.stopPropagation();
    setError(null);
    if (!label.trim()) {
      setError('question required');
      return;
    }
    const options = wantsOptions(fieldType) ? parseOptionsText(optionsText) : [];
    if (wantsOptions(fieldType) && options.length === 0) {
      setError('add at least one option');
      return;
    }
    if (options.some((option) => option.length > MAX_OPTION_LENGTH)) {
      setError(`options must be ${String(MAX_OPTION_LENGTH)} characters or fewer`);
      return;
    }
    if (fieldType === 'multiselect' && options.some((option) => option.includes(','))) {
      setError('options cannot contain commas');
      return;
    }
    onSave({
      id: existing?.id ?? newQuestionId(),
      label: label.trim(),
      fieldType,
      options,
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
            setFieldType(e.target.value as RsvpQuestionType);
          }}
          options={RSVP_QUESTION_TYPE_OPTIONS.map((o) => ({
            value: o.value,
            label: o.label,
          }))}
        />
        {wantsOptions(fieldType) ? (
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
          <Button variant="ghost" onClick={onClose} type="button">
            cancel
          </Button>
          <Button type="submit">save</Button>
        </div>
      </form>
    </Dialog>
  );
}
