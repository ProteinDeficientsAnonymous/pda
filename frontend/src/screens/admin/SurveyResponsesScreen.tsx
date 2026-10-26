import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import {
  downloadSurveyResponsesCsv,
  type SurveyPollTallyRow,
  type SurveyQuestionSummary,
  type SurveyResponseAdmin,
  useAdminSurvey,
  useDeleteSurveyResponse,
  useFinalizeSurveyPoll,
  useSurveyPollTallies,
  useSurveyQuestionSummaries,
  useSurveyResponses,
} from '@/api/surveyAdmin';
import { formatPollOption } from '@/components/questions/pollOption';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useConfirm } from '@/components/ui/useConfirm';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import {
  ALL_EVENTS,
  eventOptions,
  filterResponsesByEvent,
  responseCountLabel,
} from './surveyResponseEvents';
import { SurveyResponsesEventFilter } from './SurveyResponsesEventFilter';
import { SurveyResponsesView } from './SurveyResponsesView';

export default function SurveyResponsesScreen() {
  const { id } = useParams<{ id: string }>();
  const surveyId = id ?? '';
  const survey = useAdminSurvey(surveyId);
  const responses = useSurveyResponses(surveyId);
  const [eventFilter, setEventFilter] = useState(ALL_EVENTS);

  const datetimeQuestions = useMemo(() => {
    if (!survey.data) return [];
    return survey.data.questions.filter((q) => q.fieldType === 'datetime_poll');
  }, [survey.data]);

  const tallies = useSurveyPollTallies(
    datetimeQuestions.length > 0 && survey.isSuccess ? surveyId : undefined,
  );
  const summaries = useSurveyQuestionSummaries(
    survey.isSuccess ? surveyId : undefined,
    eventFilter,
  );
  const deleteResponse = useDeleteSurveyResponse(surveyId);
  const { confirm, element: confirmElement } = useConfirm();

  async function askDeleteResponse(response: SurveyResponseAdmin) {
    const ok = await confirm({
      title: 'delete response',
      message: "delete this response? this can't be undone.",
      confirmLabel: 'delete',
      destructive: true,
    });
    if (!ok) return;
    deleteResponse.mutate(response.id, {
      onError: (err) => {
        toast.error(extractApiErrorOr(err, "couldn't delete that response — try again"));
      },
    });
  }

  if (survey.isPending || responses.isPending) return <ContentLoading />;
  if (survey.isError || responses.isError) {
    return <ContentError message="couldn't load responses — try refreshing" />;
  }

  const visibleResponses = filterResponsesByEvent(responses.data, eventFilter);
  const firstDatetimeQuestion = datetimeQuestions[0];
  const finalizeOptions =
    !survey.data.pollResult && firstDatetimeQuestion && firstDatetimeQuestion.options.length > 0
      ? firstDatetimeQuestion.options
      : null;

  return (
    <ContentContainer>
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-medium tracking-tight break-words">{survey.data.title}</h1>
          <p className="text-muted text-sm">
            {responseCountLabel(visibleResponses.length, responses.data.length)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DownloadCsvButton
            surveyId={surveyId}
            slug={survey.data.slug}
            disabled={responses.data.length === 0}
          />
          <Link
            to={`/admin/surveys/${surveyId}`}
            className="text-foreground-secondary hover:bg-surface-dim inline-flex h-10 items-center rounded-md px-4 text-sm"
          >
            ← back to editor
          </Link>
        </div>
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

      {summaries.isError || (summaries.data?.length ?? 0) > 0 ? (
        <section className="mb-8">
          <h2 className="text-muted mb-3 text-xs font-medium tracking-wide">question summaries</h2>
          {summaries.isError ? (
            <p className="text-muted text-sm">couldn't load summaries</p>
          ) : (
            <QuestionSummaries questions={survey.data.questions} rows={summaries.data ?? []} />
          )}
        </section>
      ) : null}

      {survey.data.feedbackEventType && eventOptions(responses.data).length > 0 ? (
        <SurveyResponsesEventFilter
          responses={responses.data}
          value={eventFilter}
          onChange={setEventFilter}
        />
      ) : null}

      {responses.data.length === 0 ? (
        <p className="text-muted text-sm">no responses yet</p>
      ) : (
        <SurveyResponsesView
          survey={survey.data}
          responses={visibleResponses}
          onDelete={(r) => {
            void askDeleteResponse(r);
          }}
        />
      )}

      {confirmElement}
    </ContentContainer>
  );
}

function DownloadCsvButton({
  surveyId,
  slug,
  disabled,
}: {
  surveyId: string;
  slug: string;
  disabled: boolean;
}) {
  const [busy, setBusy] = useState(false);

  async function onClick() {
    setBusy(true);
    try {
      await downloadSurveyResponsesCsv(surveyId, slug);
    } catch {
      toast.error("couldn't download csv");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Button
      type="button"
      variant="secondary"
      disabled={disabled || busy}
      onClick={() => void onClick()}
    >
      {busy ? 'preparing…' : 'download csv'}
    </Button>
  );
}

function orderedCounts(counts: Record<string, number>, options: string[]): [string, number][] {
  // js enumerates integer-like keys numerically, which would reorder options like "2024"/"2023".
  const known = options.filter((o) => o in counts);
  const rest = Object.keys(counts).filter((o) => !known.includes(o));
  return [...known, ...rest].map((o): [string, number] => [o, counts[o] ?? 0]);
}

function QuestionSummaries({
  questions,
  rows,
}: {
  questions: { id: string; label: string; options: string[] }[];
  rows: SurveyQuestionSummary[];
}) {
  const byId = new Map(questions.map((q) => [q.id, q]));
  return (
    <div className="flex flex-col gap-4">
      {rows.map((row) => {
        const question = byId.get(row.questionId);
        return (
          <div key={row.questionId} className="border-border bg-surface rounded-lg border p-3">
            <p className="text-foreground mb-1 text-sm font-medium">
              {(question?.label ?? row.questionId).toLowerCase()}
            </p>
            <p className="text-muted mb-2 text-xs">
              {String(row.answered)} answered
              {row.mean === null ? '' : ` · average ${row.mean.toFixed(2)}`}
            </p>
            <table className="w-full text-left text-xs">
              <thead className="text-muted">
                <tr>
                  <th className="py-1 pe-2">option</th>
                  <th className="px-2 py-1">count</th>
                  <th className="px-2 py-1">share</th>
                </tr>
              </thead>
              <tbody>
                {orderedCounts(row.counts, question?.options ?? []).map(([option, count]) => (
                  <tr key={option} className="border-border border-t">
                    <td className="text-foreground py-1 pe-2">{option.toLowerCase()}</td>
                    <td className="px-2 py-1">{String(count)}</td>
                    <td className="text-muted px-2 py-1">
                      {row.answered === 0
                        ? '—'
                        : `${String(Math.round((count / row.answered) * 100))}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
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
                    <td className="text-foreground py-1 pe-2 font-mono">{formatPollOption(opt)}</td>
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
                <span className="font-mono text-xs">{formatPollOption(opt)}</span>
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
  return extractApiErrorOr(err, 'request failed');
}
