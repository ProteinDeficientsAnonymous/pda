import { QuestionType } from '@/api/questionTypes';
import type { Survey, SurveyResponseAdmin } from '@/api/surveyAdmin';
import { renderAnswer } from '@/components/questions/renderAnswer';
import { Button } from '@/components/ui/Button';

import { ExpandableAnswer, WRAP_TEXT } from './ExpandableAnswer';
import { formatSubmittedAt, submitterLabel } from './surveyResponseFormat';

// Widths live on an inner div: browsers ignore max-width on table cells.
const QUESTION_WIDTH = 'min-w-48 max-w-80';
// Choice answers are one option per line, so line counts would clamp short lists.
const FREE_TEXT_TYPES = new Set<string>([QuestionType.Text, QuestionType.Textarea]);
const STICKY_CELL = 'border-border sticky left-0 z-10 border-r px-3 py-2';

export function SurveyResponsesTable({
  survey,
  responses,
  onDelete,
}: {
  survey: Survey;
  responses: SurveyResponseAdmin[];
  onDelete: (response: SurveyResponseAdmin) => void;
}) {
  const showEvent = Boolean(survey.feedbackEventType);
  const questions = survey.questions.filter((q) => q.fieldType !== QuestionType.Section);
  return (
    <div className="border-border bg-surface overflow-x-auto rounded-lg border">
      <table className="w-full text-left text-sm">
        <thead className="bg-background text-muted text-xs">
          <tr>
            {showEvent ? <th className={`bg-background ${STICKY_CELL}`}>event</th> : null}
            <th className="px-3 py-2">submitted by</th>
            <th className="px-3 py-2">at</th>
            {questions.map((q) => (
              <th key={q.id} className="px-3 py-2">
                <div className={QUESTION_WIDTH}>{q.label}</div>
              </th>
            ))}
            <th className="px-3 py-2">
              <span className="sr-only">actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {responses.map((r) => (
            <tr key={r.id} className="border-border border-t align-top">
              {showEvent ? (
                <td className={`bg-surface text-foreground ${STICKY_CELL}`}>
                  <div className="min-w-40">{r.eventTitle?.toLowerCase() ?? '—'}</div>
                </td>
              ) : null}
              <td className="text-foreground px-3 py-2">
                {submitterLabel(r.userName, survey.anonymous)}
              </td>
              <td className="text-muted px-3 py-2 text-xs whitespace-nowrap">
                {formatSubmittedAt(r.submittedAt, survey.anonymous)}
              </td>
              {questions.map((q) => (
                <td key={q.id} className="text-foreground px-3 py-2">
                  <div className={QUESTION_WIDTH}>
                    {FREE_TEXT_TYPES.has(q.fieldType) ? (
                      <ExpandableAnswer text={renderAnswer(r.answers[q.id])} />
                    ) : (
                      <div className={WRAP_TEXT}>{renderAnswer(r.answers[q.id])}</div>
                    )}
                  </div>
                </td>
              ))}
              <td className="px-3 py-2 text-right">
                <Button
                  variant="ghost"
                  onClick={() => {
                    onDelete(r);
                  }}
                >
                  delete
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
