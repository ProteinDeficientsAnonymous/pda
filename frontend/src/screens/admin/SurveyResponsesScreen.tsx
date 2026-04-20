// Responses viewer: per-question columns plus aggregate tallies for datetime
// polls (GET /surveys/{id}/tallies/) and finalize flow when the poll is open.

import { format } from 'date-fns';
import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { isAxiosError } from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import {
  useAdminSurvey,
  useFinalizeSurveyPoll,
  useSurveyPollTallies,
  useSurveyResponses,
  type SurveyPollTallyRow,
} from '@/api/surveyAdmin';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export default function SurveyResponsesScreen() {
  const { id } = useParams<{ id: string }>();
  const surveyId = id ?? '';
  const survey = useAdminSurvey(surveyId);
  const responses = useSurveyResponses(surveyId);

  const datetimeQuestions = useMemo(() => {
    if (!survey.data) return [];
    return survey.data.questions.filter((q) => q.fieldType === 'datetime_poll');
  }, [survey.data]);

  const tallies = useSurveyPollTallies(
    datetimeQuestions.length > 0 && survey.isSuccess ? surveyId : undefined,
  );

  if (survey.isPending || responses.isPending) return <ContentLoading />;
  if (survey.isError || responses.isError) {
    return <ContentError message="couldn't load responses — try refreshing" />;
  }

  const firstDatetimeQuestion = datetimeQuestions[0];
  const finalizeOptions =
    !survey.data.pollResult && firstDatetimeQuestion && firstDatetimeQuestion.options.length > 0
      ? firstDatetimeQuestion.options
      : null;

  return (
    <ContentContainer>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-medium tracking-tight">{survey.data.title}</h1>
          <p className="text-muted text-sm">
            {String(responses.data.length)} response{responses.data.length === 1 ? '' : 's'}
          </p>
        </div>
        <Link
          to={`/admin/surveys/${surveyId}`}
          className="text-foreground-secondary hover:bg-surface-dim inline-flex h-10 items-center rounded-md px-4 text-sm"
        >
          ← back to editor
        </Link>
      </header>

      {datetimeQuestions.length > 0 ? (
        <section className="mb-8">
          <h2 className="text-muted mb-3 text-xs font-medium tracking-wide">poll tallies</h2>
          {tallies.isPending ? (
            <p className="text-muted text-sm">loading tallies…</p>
          ) : tallies.isError ? (
            <p className="text-muted text-sm">couldn't load tallies</p>
          ) : (
            <TalliesTables questions={survey.data.questions} rows={tallies.data} />
          )}
          {finalizeOptions ? (
            <SurveyFinalizeControls surveyId={surveyId} options={finalizeOptions} />
          ) : null}
        </section>
      ) : null}

      {responses.data.length === 0 ? (
        <p className="text-muted text-sm">no responses yet</p>
      ) : (
        <div className="border-border bg-surface overflow-x-auto rounded-lg border">
          <table className="w-full text-left text-sm">
            <thead className="bg-background text-muted text-xs">
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
                <tr key={r.id} className="border-border border-t align-top">
                  <td className="text-foreground px-3 py-2">{r.userName ?? '—'}</td>
                  <td className="text-muted px-3 py-2 text-xs">
                    {format(new Date(r.submittedAt), 'MMM d, yyyy h:mm a').toLowerCase()}
                  </td>
                  {survey.data.questions.map((q) => (
                    <td key={q.id} className="text-foreground px-3 py-2 whitespace-pre-wrap">
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

function TalliesTables({
  questions,
  rows,
}: {
  questions: { id: string; label: string }[];
  rows: SurveyPollTallyRow[];
}) {
  const labelById = new Map(questions.map((q) => [q.id, q.label]));
  return (
    <div className="flex flex-col gap-4">
      {rows.map((row) => (
        <div key={row.questionId} className="border-border bg-surface rounded-lg border p-3">
          <p className="text-foreground mb-2 text-sm font-medium">
            {(labelById.get(row.questionId) ?? row.questionId).toLowerCase()}
          </p>
          <p className="text-muted mb-2 text-xs">
            total responses recorded: {String(row.totalResponses)}
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-muted">
                <tr>
                  <th className="py-1 pe-2">option</th>
                  <th className="px-2 py-1">yes</th>
                  <th className="px-2 py-1">maybe</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(row.tallies).map(([opt, counts]) => (
                  <tr key={opt} className="border-border border-t">
                    <td className="text-foreground py-1 pe-2 font-mono">
                      {formatOptionLabel(opt)}
                    </td>
                    <td className="px-2 py-1">{String(counts.yes ?? 0)}</td>
                    <td className="px-2 py-1">{String(counts.maybe ?? 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

function formatOptionLabel(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.toLowerCase();
  return format(d, 'MMM d, yyyy h:mm a').toLowerCase();
}

function SurveyFinalizeControls({ surveyId, options }: { surveyId: string; options: string[] }) {
  const [open, setOpen] = useState(false);
  const [choice, setChoice] = useState(options[0] ?? '');
  const finalize = useFinalizeSurveyPoll(surveyId);

  async function onConfirm() {
    const dt = new Date(choice);
    if (Number.isNaN(dt.getTime())) {
      toast.error('pick a valid option');
      return;
    }
    try {
      await finalize.mutateAsync(dt);
      toast.success('poll finalized 🌱');
      setOpen(false);
    } catch (err) {
      toast.error(extractApiDetail(err));
    }
  }

  return (
    <div className="mt-4 flex flex-col gap-2">
      <Button
        type="button"
        variant="secondary"
        onClick={() => {
          setOpen(true);
        }}
      >
        finalize poll
      </Button>
      <Dialog
        open={open}
        onClose={() => {
          setOpen(false);
        }}
        title="finalize survey poll"
      >
        <div className="flex max-h-[70vh] flex-col gap-3 overflow-y-auto p-4">
          <p className="text-muted text-sm">
            pick the winning datetime. this locks the survey and, if linked, updates the event start
            time.
          </p>
          <div className="flex flex-col gap-2">
            {options.map((opt) => (
              <label
                key={opt}
                className="border-border flex cursor-pointer items-start gap-2 rounded-md border p-2 text-sm"
              >
                <input
                  type="radio"
                  name="win-opt"
                  checked={choice === opt}
                  onChange={() => {
                    setChoice(opt);
                  }}
                  className="mt-1"
                />
                <span className="font-mono text-xs">{formatOptionLabel(opt)}</span>
              </label>
            ))}
          </div>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setOpen(false);
              }}
            >
              cancel
            </Button>
            <Button type="button" disabled={finalize.isPending} onClick={() => void onConfirm()}>
              {finalize.isPending ? 'finalizing…' : 'confirm'}
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}

function extractApiDetail(err: unknown): string {
  if (isAxiosError(err)) {
    const d = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (d) return d;
  }
  return 'request failed';
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
