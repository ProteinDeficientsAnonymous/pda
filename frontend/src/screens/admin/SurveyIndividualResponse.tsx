import { useState } from 'react';

import { QuestionType } from '@/api/questionTypes';
import type { Survey, SurveyResponseAdmin } from '@/api/surveyAdmin';
import { renderAnswer } from '@/components/questions/renderAnswer';
import { Button } from '@/components/ui/Button';

import { formatSubmittedAt } from './formatSubmittedAt';

export function SurveyIndividualResponse({
  survey,
  responses,
  onDelete,
}: {
  survey: Survey;
  responses: SurveyResponseAdmin[];
  onDelete: (response: SurveyResponseAdmin) => void;
}) {
  const [index, setIndex] = useState(0);
  // Clamp so a delete or filter change never leaves the index past the end.
  const current = Math.min(index, responses.length - 1);
  const response = responses[current];
  if (!response) return <p className="text-muted text-sm">no responses to show 🌿</p>;

  const meta = [
    response.userName ?? '—',
    formatSubmittedAt(response.submittedAt, survey.anonymous),
    survey.feedbackEventType ? (response.eventTitle?.toLowerCase() ?? '—') : null,
  ].filter((part) => part !== null);

  return (
    <div className="border-border bg-surface rounded-lg border">
      <div className="border-border flex flex-wrap items-center justify-between gap-2 border-b px-2 py-1">
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            aria-label="previous response"
            disabled={current === 0}
            onClick={() => {
              setIndex(current - 1);
            }}
          >
            ←
          </Button>
          <span className="text-muted text-sm">
            {String(current + 1)} of {String(responses.length)}
          </span>
          <Button
            variant="ghost"
            aria-label="next response"
            disabled={current === responses.length - 1}
            onClick={() => {
              setIndex(current + 1);
            }}
          >
            →
          </Button>
        </div>
        <Button
          variant="ghost"
          onClick={() => {
            onDelete(response);
          }}
        >
          delete
        </Button>
      </div>
      <div className="flex flex-col gap-4 p-4">
        <p className="text-muted text-xs">{meta.join(' · ')}</p>
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
                  {renderAnswer(response.answers[q.id])}
                </p>
              </div>
            ),
          )}
        </div>
      </div>
    </div>
  );
}
