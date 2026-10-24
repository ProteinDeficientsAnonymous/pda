import type { ReactNode } from 'react';
import { useEffect, useRef, useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import { QuestionType } from '@/api/questionTypes';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { Toggle } from '@/components/ui/Toggle';
import { cn } from '@/utils/cn';

import type { QuestionAuthorValues } from './QuestionAuthorDialog';
import { QuestionCardOptions } from './QuestionCardOptions';
import {
  normalizeQuestionOptions,
  normalizeRatingLabels,
  questionTypeWantsOptions,
} from './questionTypeOptions';
import { RatingLabelFields } from './RatingLabelFields';

interface TypeOption<T extends string> {
  value: T;
  label: string;
}

interface Props<T extends string> {
  id: string;
  value: QuestionAuthorValues<T>;
  typeOptions: TypeOption<T>[];
  onSave: (values: QuestionAuthorValues<T>) => Promise<unknown>;
  onDuplicate?: (() => void) | undefined;
  onDelete?: (() => void) | undefined;
  focusOnMount?: boolean;
  disabled?: boolean;
  /** Extra controls rendered under the options; state and saving live in the caller. */
  extraFields?: ReactNode;
  errorFallback?: string;
}

type SaveStatus =
  | { kind: 'idle' }
  | { kind: 'saving' }
  | { kind: 'saved' }
  | { kind: 'error'; message: string };

// Rating options are optional star labels, so only the choice types need one.
function optionsRequired(fieldType: string): boolean {
  return questionTypeWantsOptions(fieldType as QuestionType) && fieldType !== QuestionType.Rating;
}

function seedOptions(fieldType: string): string[] {
  return optionsRequired(fieldType) && fieldType !== QuestionType.DatetimePoll ? ['option 1'] : [];
}

const CHOICE_TYPES: ReadonlySet<string> = new Set([
  QuestionType.Radio,
  QuestionType.Select,
  QuestionType.Checkbox,
]);

// Choice options carry over between choice types; poll dates and star labels don't.
function sharesOptions(from: string, to: string): boolean {
  return CHOICE_TYPES.has(from) && CHOICE_TYPES.has(to);
}

function normalizeOptions(fieldType: string, options: readonly string[]): string[] {
  if (fieldType === QuestionType.Rating) return normalizeRatingLabels(options);
  if (!questionTypeWantsOptions(fieldType as QuestionType)) return [];
  return normalizeQuestionOptions(options);
}

function normalize<T extends string>(values: QuestionAuthorValues<T>): QuestionAuthorValues<T> {
  return {
    ...values,
    label: values.label.trim(),
    options: normalizeOptions(values.fieldType, values.options),
  };
}

function validationError<T extends string>(values: QuestionAuthorValues<T>): string | null {
  if (!values.label) return 'question text required';
  if (optionsRequired(values.fieldType) && values.options.length === 0) {
    return 'add at least one option';
  }
  return null;
}

export function QuestionCardEditor<T extends string>({
  id,
  value,
  typeOptions,
  onSave,
  onDuplicate,
  onDelete,
  focusOnMount = false,
  disabled = false,
  extraFields,
  errorFallback = "couldn't save — try again",
}: Props<T>) {
  const [draft, setDraft] = useState<QuestionAuthorValues<T>>(() => ({
    ...value,
    options: [...value.options],
  }));
  const [status, setStatus] = useState<SaveStatus>({ kind: 'idle' });
  const lastSaved = useRef(JSON.stringify(normalize(value)));
  const saveQueue = useRef<Promise<void>>(Promise.resolve());
  const labelRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!focusOnMount) return;
    labelRef.current?.focus();
    labelRef.current?.select();
  }, [focusOnMount]);

  function commit(next: QuestionAuthorValues<T>) {
    setDraft(next);
    const normalized = normalize(next);
    const error = validationError(normalized);
    if (error) {
      setStatus({ kind: 'error', message: error });
      return;
    }
    // Queued so each save compares against the previous one's result, not a stale lastSaved.
    saveQueue.current = saveQueue.current.then(() => persist(normalized));
  }

  async function persist(normalized: QuestionAuthorValues<T>) {
    const serialized = JSON.stringify(normalized);
    if (serialized === lastSaved.current) {
      setStatus((s) => (s.kind === 'error' ? { kind: 'idle' } : s));
      return;
    }
    setStatus({ kind: 'saving' });
    try {
      await onSave(normalized);
      lastSaved.current = serialized;
      setStatus({ kind: 'saved' });
    } catch (err) {
      setStatus({ kind: 'error', message: extractApiErrorOr(err, errorFallback) });
    }
  }

  function changeType(fieldType: T) {
    const keepOptions =
      sharesOptions(draft.fieldType, fieldType) && draft.options.some((o) => o.trim());
    const options = keepOptions ? draft.options : seedOptions(fieldType);
    commit({ ...draft, fieldType, options });
  }

  const wantsOptions = questionTypeWantsOptions(draft.fieldType as QuestionType);

  return (
    <article
      aria-label={draft.label || 'untitled question'}
      className={cn(
        'border-border bg-surface flex flex-col gap-3 rounded-lg border p-4',
        status.kind === 'error' && 'border-destructive-border',
      )}
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start">
        <div className="min-w-0 flex-1">
          <TextField
            ref={labelRef}
            id={`${id}-label`}
            label="question"
            hideLabel
            placeholder="question"
            value={draft.label}
            disabled={disabled}
            maxLength={200}
            onChange={(e) => {
              setDraft((d) => ({ ...d, label: e.target.value }));
            }}
            onBlur={() => {
              commit(draft);
            }}
          />
        </div>
        <div className="sm:w-48">
          <Select
            id={`${id}-type`}
            label="question type"
            hideLabel
            value={draft.fieldType}
            disabled={disabled}
            options={typeOptions}
            onChange={(e) => {
              changeType(e.target.value as T);
            }}
          />
        </div>
      </div>

      {draft.fieldType === QuestionType.Rating ? (
        <RatingLabelFields
          id={id}
          options={draft.options}
          disabled={disabled}
          onChange={(options) => {
            setDraft((d) => ({ ...d, options }));
          }}
          onCommit={(options) => {
            commit({ ...draft, options });
          }}
        />
      ) : wantsOptions ? (
        <QuestionCardOptions
          id={id}
          fieldType={draft.fieldType}
          options={draft.options}
          disabled={disabled}
          onChange={(options) => {
            setDraft((d) => ({ ...d, options }));
          }}
          onCommit={(options) => {
            commit({ ...draft, options });
          }}
        />
      ) : null}

      {extraFields}

      <footer className="border-border flex flex-wrap items-center justify-end gap-x-1 gap-y-1 border-t pt-3 sm:gap-x-2">
        <SaveStatusText status={status} />
        {disabled ? null : (
          <>
            {onDuplicate ? (
              <Button variant="ghost" className="h-9 px-2 sm:px-3" onClick={onDuplicate}>
                duplicate
              </Button>
            ) : null}
            {onDelete ? (
              <Button variant="ghost" className="h-9 px-2 sm:px-3" onClick={onDelete}>
                delete
              </Button>
            ) : null}
            <span aria-hidden="true" className="bg-border mx-1 hidden h-6 w-px sm:block" />
            <Toggle
              label="required"
              checked={draft.required}
              onChange={(required) => {
                commit({ ...draft, required });
              }}
            />
          </>
        )}
      </footer>
    </article>
  );
}

function SaveStatusText({ status }: { status: SaveStatus }) {
  if (status.kind === 'error') {
    return (
      <p role="alert" className="text-destructive me-auto text-xs">
        {status.message}
      </p>
    );
  }
  const text = status.kind === 'saving' ? 'saving…' : status.kind === 'saved' ? 'saved' : '';
  return (
    <p aria-live="polite" className="text-muted me-auto text-xs">
      {text}
    </p>
  );
}
