import { useQueryClient } from '@tanstack/react-query';
import type { SyntheticEvent } from 'react';
import { useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';

import { extractApiErrorOr, hasErrorCode } from '@/api/apiErrors';
import { type AnswerValue, type Survey, useSubmitSurvey, useSurvey } from '@/api/surveys';
import { clearStoredSurveyToken, getStoredSurveyToken } from '@/api/surveyTokenStorage';
import { Code } from '@/api/validationCodes';
import { useAuthStore } from '@/auth/store';
import { QuestionField } from '@/components/questions/QuestionField';
import { visibleQuestionIds } from '@/components/questions/questionVisibility';
import { Button } from '@/components/ui/Button';
import { type SurveyStatus, surveyStatus } from '@/models/survey';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

export default function SurveyScreen() {
  const { slug } = useParams<{ slug: string }>();
  const { data: survey, isPending, isError } = useSurvey(slug);
  const navigate = useNavigate();
  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the survey — try refreshing" />;
  const status = surveyStatus(survey, { checkCap: survey.myResponseId === null });
  // A finalized poll keeps rendering its result rather than a shut-door message.
  if (status !== 'active' && survey.pollResult === null) {
    return <SurveyUnavailable survey={survey} status={status} />;
  }
  return (
    <SurveyForm
      survey={survey}
      onSubmitted={() => {
        void navigate(`/surveys/${survey.slug}/thanks`);
      }}
    />
  );
}

const UNAVAILABLE_MESSAGE: Record<Exclude<SurveyStatus, 'active'>, string> = {
  scheduled: "this survey isn't open yet — check back when it opens",
  capped: 'this survey has reached its response limit',
  closed: 'this survey is closed — responses are no longer accepted',
};

function SurveyUnavailable({
  survey,
  status,
}: {
  survey: Survey;
  status: Exclude<SurveyStatus, 'active'>;
}) {
  return (
    <ContentContainer>
      <h1 className="mb-2 text-2xl font-medium tracking-tight">{survey.title}</h1>
      {survey.description ? (
        <p className="text-foreground-tertiary mb-6 text-sm">{survey.description}</p>
      ) : null}
      <p
        role="status"
        className="bg-surface-dim text-foreground-secondary rounded-md px-3 py-2 text-sm"
      >
        {UNAVAILABLE_MESSAGE[status]}
      </p>
    </ContentContainer>
  );
}

function hydrateAnswers(survey: Survey): Record<string, AnswerValue> {
  const out: Record<string, AnswerValue> = {};
  if (!survey.myAnswers) return out;
  for (const [qid, entry] of Object.entries(survey.myAnswers)) {
    out[qid] = entry.answer;
  }
  return out;
}

function SurveyForm({ survey, onSubmitted }: { survey: Survey; onSubmitted: () => void }) {
  const qc = useQueryClient();
  const [editingId, setEditingId] = useState(survey.myResponseId);
  const submit = useSubmitSurvey(survey.slug, editingId);
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  // Lazy init so the user's prior response loads exactly once when the form
  // mounts. Subsequent server updates (e.g. poll finalized) re-render the
  // parent but preserve what the user is currently typing.
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>(() => hydrateAnswers(survey));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);

  const finalized = survey.pollResult !== null;
  const readOnly = finalized;

  const visible = visibleQuestionIds(survey.questions, answers);
  const shownQuestions = survey.questions.filter((q) => visible.has(q.id));

  function validate(): boolean {
    const next: Record<string, string> = {};
    for (const q of shownQuestions) {
      if (!q.required) continue;
      const a = answers[q.id];
      if (a === undefined) {
        next[q.id] = 'required';
      } else if (typeof a === 'string' && !a.trim()) {
        next[q.id] = 'required';
      } else if (typeof a === 'object' && Object.keys(a).length === 0) {
        next[q.id] = 'pick at least one';
      }
    }
    setErrors(next);
    const firstMissing = shownQuestions.find((q) => next[q.id]);
    if (!firstMissing) return true;
    toast.error('answer the required questions before submitting', { id: 'survey-required' });
    const field = formRef.current?.querySelector(`[data-question-id="${firstMissing.id}"]`);
    field?.scrollIntoView({ block: 'center', behavior: 'smooth' });
    field
      ?.querySelector<HTMLElement>('input, select, textarea, button')
      ?.focus({ preventScroll: true });
    return false;
  }

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setServerError(null);
    if (!validate()) return;
    // Strip empties before submit to match Flutter behavior.
    const payload: Record<string, AnswerValue> = {};
    for (const [qid, val] of Object.entries(answers)) {
      if (!visible.has(qid)) continue;
      if (typeof val === 'string' && !val.trim()) continue;
      if (typeof val === 'object' && Object.keys(val).length === 0) continue;
      payload[qid] = val;
    }
    try {
      await submit.mutateAsync(payload);
      onSubmitted();
    } catch (err) {
      setServerError(extractError(err));
      // Survey closed between load and submit — refetch so the closed state renders.
      if (hasErrorCode(err, Code.Survey.Closed)) {
        void qc.invalidateQueries({ queryKey: ['survey', survey.slug] });
      }
    }
  }

  const submitLabel = editingId ? 'update response' : 'submit';
  const canSubmitAnother = !readOnly && !survey.oneResponsePerUser && editingId !== null;
  const canStartFresh =
    !isAuthed && !readOnly && survey.myResponseId !== null && getStoredSurveyToken(survey.slug);

  function resetForm() {
    setEditingId(null);
    setAnswers({});
    setErrors({});
    setServerError(null);
    submit.reset();
  }

  function startNewResponse() {
    clearStoredSurveyToken(survey.slug);
    resetForm();
    void qc.invalidateQueries({ queryKey: ['survey', survey.slug] });
  }

  return (
    <ContentContainer>
      <h1 className="mb-2 text-2xl font-medium tracking-tight">{survey.title}</h1>
      {survey.description ? (
        <p className="text-foreground-tertiary mb-6 text-sm">{survey.description}</p>
      ) : null}

      {survey.anonymous ? (
        <p className="text-foreground-secondary mb-6 text-sm">
          responses are anonymous — your name isn't saved with your answers
        </p>
      ) : null}

      {finalized ? (
        <div className="bg-surface-dim text-foreground-secondary mb-6 rounded-md px-3 py-2 text-sm">
          this poll has been finalized — responses are locked
        </div>
      ) : null}

      <form
        ref={formRef}
        onSubmit={(e) => void onSubmit(e)}
        className="flex flex-col gap-5"
        noValidate
      >
        {shownQuestions.map((q) => (
          <div key={q.id} data-question-id={q.id}>
            <QuestionField
              question={q}
              value={answers[q.id]}
              onChange={(v) => {
                setAnswers((a) => ({ ...a, [q.id]: v }));
              }}
              error={errors[q.id]}
              readOnly={readOnly}
            />
          </div>
        ))}

        {serverError ? (
          <p role="alert" className="text-sm text-red-600">
            {serverError}
          </p>
        ) : null}

        {!readOnly ? (
          <Button type="submit" disabled={submit.isPending}>
            {submit.isPending ? 'saving…' : submitLabel}
          </Button>
        ) : null}

        {canSubmitAnother ? (
          <button
            type="button"
            onClick={resetForm}
            className="text-foreground-tertiary self-start text-sm underline"
          >
            submit another response
          </button>
        ) : null}

        {canStartFresh ? (
          <button
            type="button"
            onClick={startNewResponse}
            className="text-foreground-tertiary self-start text-sm underline"
          >
            not you? start a new response
          </button>
        ) : null}
      </form>
    </ContentContainer>
  );
}

function extractError(err: unknown): string {
  return extractApiErrorOr(err, "couldn't submit — try again");
}
