import { useState } from 'react';
import { isAxiosError } from 'axios';
import { useParams } from 'react-router-dom';
import { useSubmitSurvey, useSurvey, type AnswerValue, type Survey } from '@/api/surveys';
import { Button } from '@/components/ui/Button';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { SurveyQuestionField } from './SurveyQuestionField';

export default function SurveyScreen() {
  const { slug } = useParams<{ slug: string }>();
  const { data: survey, isPending, isError } = useSurvey(slug);
  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the survey — try refreshing" />;
  return <SurveyForm survey={survey} />;
}

function hydrateAnswers(survey: Survey): Record<string, AnswerValue> {
  const out: Record<string, AnswerValue> = {};
  if (!survey.myAnswers) return out;
  for (const [qid, entry] of Object.entries(survey.myAnswers)) {
    out[qid] = entry.answer;
  }
  return out;
}

function SurveyForm({ survey }: { survey: Survey }) {
  const submit = useSubmitSurvey(survey.slug);
  // Lazy init so the user's prior response loads exactly once when the form
  // mounts. Subsequent server updates (e.g. poll finalized) re-render the
  // parent but preserve what the user is currently typing.
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>(() => hydrateAnswers(survey));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);

  const finalized = survey.pollResult !== null;
  const readOnly = finalized;

  function validate(): boolean {
    const next: Record<string, string> = {};
    for (const q of survey.questions) {
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
    return Object.keys(next).length === 0;
  }

  async function onSubmit(e: React.SyntheticEvent) {
    e.preventDefault();
    setServerError(null);
    if (!validate()) return;
    // Strip empties before submit to match Flutter behavior.
    const payload: Record<string, AnswerValue> = {};
    for (const [qid, val] of Object.entries(answers)) {
      if (typeof val === 'string' && !val.trim()) continue;
      if (typeof val === 'object' && Object.keys(val).length === 0) continue;
      payload[qid] = val;
    }
    try {
      await submit.mutateAsync(payload);
    } catch (err) {
      setServerError(extractError(err));
    }
  }

  const submitLabel = survey.myResponseId ? 'update response' : 'submit';

  return (
    <ContentContainer>
      <h1 className="mb-2 text-2xl font-medium tracking-tight">{survey.title}</h1>
      {survey.description ? (
        <p className="mb-6 text-sm text-neutral-600">{survey.description}</p>
      ) : null}

      {finalized ? (
        <div className="mb-6 rounded-md bg-neutral-100 px-3 py-2 text-sm text-neutral-700">
          this poll has been finalized — responses are locked
        </div>
      ) : null}

      <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-5" noValidate>
        {survey.questions.map((q) => (
          <SurveyQuestionField
            key={q.id}
            question={q}
            value={answers[q.id]}
            onChange={(v) => {
              setAnswers((a) => ({ ...a, [q.id]: v }));
            }}
            error={errors[q.id]}
            readOnly={readOnly}
          />
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

        {submit.isSuccess && !readOnly ? <p className="text-sm text-green-700">saved ✓</p> : null}
      </form>
    </ContentContainer>
  );
}

function extractError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't submit — try again";
}
