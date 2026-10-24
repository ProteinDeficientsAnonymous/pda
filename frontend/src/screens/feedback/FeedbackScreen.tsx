import { format } from 'date-fns';
import type { SyntheticEvent } from 'react';
import { useState } from 'react';
import { useLocation } from 'react-router-dom';

import { extractApiErrorOr, hasErrorCode } from '@/api/apiErrors';
import { type EventFeedback, useEventFeedback, useSubmitEventFeedback } from '@/api/eventFeedback';
import type { AnswerValue, Survey } from '@/api/surveys';
import { Code } from '@/api/validationCodes';
import { QuestionField } from '@/components/questions/QuestionField';
import { visibleQuestionIds } from '@/components/questions/questionVisibility';
import { Button } from '@/components/ui/Button';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

const INVALID_LINK = "this feedback link doesn't work — it may have expired";
const CLOSED = 'feedback for this event is closed';
const ALREADY_SHARED = 'you already shared feedback for this one — thank you 🌱';

export default function FeedbackScreen() {
  const token = useLocation().hash.replace(/^#/, '');
  const { data, error, isPending, isError } = useEventFeedback(token);
  const [override, setOverride] = useState<'closed' | 'already' | null>(null);

  if (!token) return <Notice message={INVALID_LINK} />;
  if (isPending) return <ContentLoading />;
  if (isError) {
    if (hasErrorCode(error, Code.Survey.FeedbackLinkInvalid))
      return <Notice message={INVALID_LINK} />;
    if (hasErrorCode(error, Code.Survey.NotFound)) return <Notice message={CLOSED} />;
    return <ContentError message="couldn't load the feedback form — try refreshing" />;
  }
  if (data.alreadyResponded || override === 'already') return <Notice message={ALREADY_SHARED} />;
  if (!data.isOpen || data.survey === null || override === 'closed') {
    return <Notice message={CLOSED} />;
  }
  return (
    <FeedbackForm
      token={token}
      feedback={data}
      survey={data.survey}
      onAlreadySubmitted={() => {
        setOverride('already');
      }}
      onClosed={() => {
        setOverride('closed');
      }}
    />
  );
}

function Notice({ message }: { message: string }) {
  return (
    <ContentContainer>
      <p
        role="status"
        className="bg-surface-dim text-foreground-secondary rounded-md px-3 py-2 text-sm"
      >
        {message}
      </p>
    </ContentContainer>
  );
}

function isEmptyAnswer(a: AnswerValue | undefined): boolean {
  if (a === undefined) return true;
  if (typeof a === 'string') return !a.trim();
  return Object.keys(a).length === 0;
}

function heading(feedback: EventFeedback): string {
  const date = feedback.eventStart
    ? ` · ${format(feedback.eventStart, 'MMM d').toLowerCase()}`
    : '';
  return `feedback for: ${feedback.eventTitle}${date}`;
}

interface FormProps {
  token: string;
  feedback: EventFeedback;
  survey: Survey;
  onAlreadySubmitted: () => void;
  onClosed: () => void;
}

function FeedbackForm({ token, feedback, survey, onAlreadySubmitted, onClosed }: FormProps) {
  const submit = useSubmitEventFeedback(token);
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);

  const visible = visibleQuestionIds(survey.questions, answers);
  const shownQuestions = survey.questions.filter((q) => visible.has(q.id));

  function validate(): boolean {
    const next: Record<string, string> = {};
    for (const q of shownQuestions) {
      if (!q.required || !isEmptyAnswer(answers[q.id])) continue;
      next[q.id] = typeof answers[q.id] === 'object' ? 'pick at least one' : 'required';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setServerError(null);
    if (!validate()) return;
    const payload: Record<string, AnswerValue> = {};
    for (const [qid, val] of Object.entries(answers)) {
      if (visible.has(qid) && !isEmptyAnswer(val)) payload[qid] = val;
    }
    try {
      await submit.mutateAsync(payload);
    } catch (err) {
      if (hasErrorCode(err, Code.Survey.FeedbackAlreadySubmitted)) {
        onAlreadySubmitted();
        return;
      }
      if (hasErrorCode(err, Code.Survey.Closed) || hasErrorCode(err, Code.Survey.NotFound)) {
        onClosed();
        return;
      }
      setServerError(extractApiErrorOr(err, "couldn't submit — try again"));
    }
  }

  if (submit.isSuccess) {
    const message = submit.data.confirmationMessage;
    return <Notice message={message ? message.toLowerCase() : 'thanks for sharing 🌱'} />;
  }

  return (
    <ContentContainer>
      <h1 className="mb-2 text-2xl font-medium tracking-tight">{heading(feedback)}</h1>
      <p className="text-foreground-secondary mb-6 text-sm">
        your answers are anonymous — hosts see what you wrote, not who wrote it
      </p>
      <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-5" noValidate>
        {shownQuestions.map((q) => (
          <QuestionField
            key={q.id}
            question={q}
            value={answers[q.id]}
            onChange={(v) => {
              setAnswers((a) => ({ ...a, [q.id]: v }));
            }}
            error={errors[q.id]}
          />
        ))}
        {serverError ? (
          <p role="alert" className="text-sm text-red-600">
            {serverError}
          </p>
        ) : null}
        <Button type="submit" disabled={submit.isPending}>
          {submit.isPending ? 'sending…' : 'submit'}
        </Button>
      </form>
    </ContentContainer>
  );
}
