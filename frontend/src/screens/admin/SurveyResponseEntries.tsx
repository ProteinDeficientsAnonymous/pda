import { useState } from 'react';

import { QuestionType } from '@/api/questionTypes';
import type { Survey, SurveyResponseAdmin } from '@/api/surveyAdmin';
import { renderAnswer } from '@/components/questions/renderAnswer';
import { Dialog } from '@/components/ui/Dialog';

import { formatSubmittedAt, submitterLabel } from './surveyResponseFormat';

export function SurveyResponseEntries({
  survey,
  responses,
}: {
  survey: Survey;
  responses: SurveyResponseAdmin[];
}) {
  const [openId, setOpenId] = useState<string | null>(null);
  const opened = responses.find((r) => r.id === openId);
  if (responses.length === 0) return <p className="text-muted text-sm">no responses to show 🌿</p>;

  return (
    <>
      <ul className="border-border bg-surface divide-border divide-y rounded-lg border">
        {responses.map((r) => (
          <li key={r.id}>
            <button
              type="button"
              onClick={() => {
                setOpenId(r.id);
              }}
              className="hover:bg-surface-dim flex w-full flex-wrap items-baseline justify-between gap-x-3 gap-y-1 px-3 py-2 text-left text-sm"
            >
              <span className="text-foreground">
                {submitterLabel(r.userName, survey.anonymous)}
              </span>
              <span className="text-muted text-xs">{entryMeta(survey, r)}</span>
            </button>
          </li>
        ))}
      </ul>
      {opened ? (
        <Dialog
          open
          wide
          title={submitterLabel(opened.userName, survey.anonymous)}
          onClose={() => {
            setOpenId(null);
          }}
        >
          <p className="text-muted mb-4 text-xs">{entryMeta(survey, opened)}</p>
          <div className="flex flex-col gap-4">
            {survey.questions.map((q) =>
              q.fieldType === QuestionType.Section ? (
                <h3
                  key={q.id}
                  className="border-border text-foreground border-b pb-1 text-sm font-medium"
                >
                  {q.label}
                </h3>
              ) : (
                <div key={q.id}>
                  <p className="text-muted text-xs">{q.label}</p>
                  <p className="text-foreground text-sm whitespace-pre-wrap">
                    {renderAnswer(opened.answers[q.id])}
                  </p>
                </div>
              ),
            )}
          </div>
        </Dialog>
      ) : null}
    </>
  );
}

function entryMeta(survey: Survey, response: SurveyResponseAdmin): string {
  const submitted = formatSubmittedAt(response.submittedAt, survey.anonymous);
  if (!survey.feedbackEventType) return submitted;
  return `${response.eventTitle?.toLowerCase() ?? '—'} · ${submitted}`;
}
