import { useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useUpdateSurvey } from '@/api/surveyAdmin';
import { Textarea } from '@/components/ui/Textarea';
import { cn } from '@/utils/cn';

interface Props {
  surveyId: string;
  field: 'description' | 'confirmationMessage';
  value: string;
  title: string;
  badge: string;
  label: string;
  hint: string;
  placeholder?: string;
  rows: number;
  maxLength: number;
  errorMessage: string;
  className?: string;
}

export function SurveyTextCard({
  surveyId,
  field,
  value,
  title,
  badge,
  label,
  hint,
  placeholder,
  rows,
  maxLength,
  errorMessage,
  className,
}: Props) {
  const update = useUpdateSurvey(surveyId);
  const [draft, setDraft] = useState(value);
  const [saved, setSaved] = useState(value);

  function save() {
    const next = draft.trim();
    if (next === saved.trim()) return;
    update.mutate(field === 'description' ? { description: next } : { confirmationMessage: next }, {
      onSuccess: () => {
        setSaved(next);
      },
    });
  }

  return (
    <article
      aria-label={title}
      className={cn(
        'border-border bg-surface-dim flex flex-col gap-3 rounded-lg border p-4',
        update.isError && 'border-destructive-border',
        className,
      )}
    >
      <header className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-medium">{title}</h3>
        <span className="text-muted text-xs">{badge}</span>
      </header>
      <Textarea
        label={label}
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value);
        }}
        onBlur={save}
        placeholder={placeholder}
        hint={hint}
        rows={rows}
        maxLength={maxLength}
      />
      {update.isError ? (
        <p role="alert" className="text-destructive text-xs">
          {extractApiErrorOr(update.error, errorMessage)}
        </p>
      ) : (
        <p aria-live="polite" className="text-muted text-xs">
          {update.isPending ? 'saving…' : update.isSuccess ? 'saved' : ''}
        </p>
      )}
    </article>
  );
}
