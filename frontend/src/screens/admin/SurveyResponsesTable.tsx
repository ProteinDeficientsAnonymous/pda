import { format, parseISO } from 'date-fns';

import type { Survey, SurveyResponseAdmin } from '@/api/surveyAdmin';
import { Button } from '@/components/ui/Button';

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
  return (
    <div className="border-border bg-surface overflow-x-auto rounded-lg border">
      <table className="w-full text-left text-sm">
        <thead className="bg-background text-muted text-xs">
          <tr>
            <th className="px-3 py-2">submitted by</th>
            <th className="px-3 py-2">at</th>
            {showEvent ? <th className="px-3 py-2">event</th> : null}
            {survey.questions.map((q) => (
              <th key={q.id} className="px-3 py-2">
                {q.label}
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
              <td className="text-foreground px-3 py-2">{r.userName ?? '—'}</td>
              <td className="text-muted px-3 py-2 text-xs">
                {formatSubmittedAt(r.submittedAt, survey.anonymous)}
              </td>
              {showEvent ? (
                <td className="text-foreground px-3 py-2">{r.eventTitle?.toLowerCase() ?? '—'}</td>
              ) : null}
              {survey.questions.map((q) => (
                <td key={q.id} className="text-foreground px-3 py-2 whitespace-pre-wrap">
                  {renderAnswer(r.answers[q.id])}
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

function formatSubmittedAt(iso: string, anonymous: boolean): string {
  // Anonymous surveys get a server-local date only; its yyyy-mm-dd prefix is that day.
  if (anonymous) return format(parseISO(iso.slice(0, 10)), 'MMM d, yyyy').toLowerCase();
  return format(new Date(iso), 'MMM d, yyyy h:mm a').toLowerCase();
}

function renderAnswer(raw: unknown): string {
  if (raw === undefined || raw === null) return '—';
  if (typeof raw === 'object' && 'answer' in (raw as Record<string, unknown>)) {
    const a = (raw as { answer: unknown }).answer;
    if (typeof a === 'string') return a;
    if (typeof a === 'object' && a !== null) {
      return Object.entries(a as Record<string, string>)
        .map(([k, v]) => `${k}: ${v}`)
        .join('\n');
    }
    return JSON.stringify(a);
  }
  return typeof raw === 'string' ? raw : JSON.stringify(raw);
}
