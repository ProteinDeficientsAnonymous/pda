import { useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useUpdateSurvey } from '@/api/surveyAdmin';
import { Textarea } from '@/components/ui/Textarea';
import { DEFAULT_THANK_YOU_MESSAGE } from '@/models/survey';
import { cn } from '@/utils/cn';

interface Props {
  surveyId: string;
  confirmationMessage: string;
}

export function SurveyThankYouCard({ surveyId, confirmationMessage }: Props) {
  const update = useUpdateSurvey(surveyId);
  const [draft, setDraft] = useState(confirmationMessage);
  const [saved, setSaved] = useState(confirmationMessage);

  function save() {
    const next = draft.trim();
    if (next === saved.trim()) return;
    update.mutate(
      { confirmationMessage: next },
      {
        onSuccess: () => {
          setSaved(next);
        },
      },
    );
  }

  return (
    <article
      aria-label="thank-you page"
      className={cn(
        'border-border bg-surface-dim mt-6 flex flex-col gap-3 rounded-lg border p-4',
        update.isError && 'border-destructive-border',
      )}
    >
      <header className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-medium">thank-you page</h3>
        <span className="text-muted text-xs">
          <span aria-hidden="true">🔒 </span>always last
        </span>
      </header>
      <Textarea
        label="thank-you message"
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value);
        }}
        onBlur={save}
        placeholder={DEFAULT_THANK_YOU_MESSAGE}
        hint="shown after someone submits — leave blank for the default"
        rows={2}
        maxLength={1000}
      />
      {update.isError ? (
        <p role="alert" className="text-destructive text-xs">
          {extractApiErrorOr(update.error, "couldn't save the message — try again")}
        </p>
      ) : (
        <p aria-live="polite" className="text-muted text-xs">
          {update.isPending ? 'saving…' : update.isSuccess ? 'saved' : ''}
        </p>
      )}
    </article>
  );
}
