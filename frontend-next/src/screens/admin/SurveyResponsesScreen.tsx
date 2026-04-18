// Responses viewer. Shows one row per submission with a column per question.
// Aggregate tallies for datetime polls live on a separate server endpoint
// (/tallies/) and we could wire those in phase 5+ — for now the raw answers
// table covers the core admin need (seeing what people wrote).

import { format } from 'date-fns';
import { Link, useParams } from 'react-router-dom';
import { useAdminSurvey, useSurveyResponses } from '@/api/surveyAdmin';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export default function SurveyResponsesScreen() {
  const { id } = useParams<{ id: string }>();
  const surveyId = id ?? '';
  const survey = useAdminSurvey(surveyId);
  const responses = useSurveyResponses(surveyId);

  if (survey.isPending || responses.isPending) return <ContentLoading />;
  if (survey.isError || responses.isError) {
    return <ContentError message="couldn't load responses — try refreshing" />;
  }

  return (
    <ContentContainer>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-medium tracking-tight">{survey.data.title}</h1>
          <p className="text-sm text-neutral-500">
            {String(responses.data.length)} response{responses.data.length === 1 ? '' : 's'}
          </p>
        </div>
        <Link
          to={`/admin/surveys/${surveyId}`}
          className="inline-flex h-10 items-center rounded-md px-4 text-sm text-neutral-700 hover:bg-neutral-100"
        >
          ← back to editor
        </Link>
      </header>

      {responses.data.length === 0 ? (
        <p className="text-sm text-neutral-500">no responses yet</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-neutral-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-neutral-50 text-xs text-neutral-500 uppercase">
              <tr>
                <th className="px-3 py-2">submitted by</th>
                <th className="px-3 py-2">at</th>
                {survey.data.questions.map((q) => (
                  <th key={q.id} className="px-3 py-2">
                    {q.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {responses.data.map((r) => (
                <tr key={r.id} className="border-t border-neutral-100 align-top">
                  <td className="px-3 py-2 text-neutral-800">{r.userName ?? '—'}</td>
                  <td className="px-3 py-2 text-xs text-neutral-500">
                    {format(new Date(r.submittedAt), 'MMM d, yyyy h:mm a')}
                  </td>
                  {survey.data.questions.map((q) => (
                    <td key={q.id} className="px-3 py-2 whitespace-pre-wrap text-neutral-800">
                      {renderAnswer(r.answers[q.id])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </ContentContainer>
  );
}

function renderAnswer(raw: unknown): string {
  if (raw === undefined || raw === null) return '—';
  // Server stores answers as { label, answer } per question.
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
