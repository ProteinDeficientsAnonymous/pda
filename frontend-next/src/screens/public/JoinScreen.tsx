import { useState } from 'react';
import { isAxiosError } from 'axios';
import { useNavigate } from 'react-router-dom';
import { AlreadyInvitedError, useJoinQuestions, useSubmitJoinRequest } from '@/api/join';
import type { JoinQuestion } from '@/api/join';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { TextField } from '@/components/ui/TextField';
import { ContentContainer, ContentError, ContentLoading } from './ContentContainer';

// Mirrors backend FieldLimit constants.
const MAX_NAME = 64;
const MAX_PHONE = 20;
const MAX_ANSWER = 2000;

// Heuristic from join_screen.dart: multi-line if the label mentions "why".
function isMultiline(q: JoinQuestion): boolean {
  return q.fieldType === 'text' && q.label.toLowerCase().includes('why');
}

export default function JoinScreen() {
  const { data: questions, isPending, isError } = useJoinQuestions();
  if (isPending) return <ContentLoading />;
  if (isError) {
    return <ContentError message="couldn't load the form — try refreshing" />;
  }
  return <JoinForm questions={questions} />;
}

function JoinForm({ questions }: { questions: readonly JoinQuestion[] }) {
  const submit = useSubmitJoinRequest();
  const navigate = useNavigate();

  const [displayName, setDisplayName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);

  function validate(): boolean {
    const next: Record<string, string> = {};
    if (!displayName.trim()) next.displayName = 'name required';
    else if (!/^[\p{L}\p{M}' \-.]+$/u.test(displayName)) next.displayName = 'letters only';
    if (!phoneNumber.trim()) next.phoneNumber = 'phone required';
    for (const q of questions) {
      const val = (answers[q.id] ?? '').trim();
      if (q.required && !val) next[q.id] = 'required';
      else if (val.length > MAX_ANSWER) next[q.id] = `under ${String(MAX_ANSWER)} chars`;
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function onSubmit(e: React.SyntheticEvent) {
    e.preventDefault();
    setServerError(null);
    if (!validate()) return;
    const nonEmpty = Object.fromEntries(Object.entries(answers).filter(([, v]) => v.trim() !== ''));
    try {
      await submit.mutateAsync({
        displayName: displayName.trim(),
        phoneNumber: phoneNumber.trim(),
        answers: nonEmpty,
      });
      void navigate('/join/success', { replace: true });
    } catch (err) {
      if (err instanceof AlreadyInvitedError) {
        void navigate('/login?invited=true', { replace: true });
        return;
      }
      setServerError(extractError(err));
    }
  }

  return (
    <ContentContainer>
      <h1 className="mb-2 text-2xl font-medium tracking-tight">request to join pda</h1>
      <p className="mb-6 text-sm text-neutral-600">
        we review all requests — you'll hear from us once a vetting member has had a look
      </p>

      <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-4" noValidate>
        <TextField
          label="display name"
          value={displayName}
          onChange={(e) => {
            setDisplayName(e.target.value);
          }}
          maxLength={MAX_NAME}
          autoComplete="name"
          error={errors.displayName}
          hint="at least first name + last initial"
          required
        />
        <TextField
          label="phone number"
          type="tel"
          value={phoneNumber}
          onChange={(e) => {
            setPhoneNumber(e.target.value);
          }}
          maxLength={MAX_PHONE}
          autoComplete="tel"
          error={errors.phoneNumber}
          hint="use the number you use (or will use) to connect with the community"
          required
        />

        {questions.map((q) => (
          <QuestionField
            key={q.id}
            question={q}
            value={answers[q.id] ?? ''}
            onChange={(val) => {
              setAnswers((a) => ({ ...a, [q.id]: val }));
            }}
            error={errors[q.id]}
          />
        ))}

        {serverError ? (
          <p role="alert" className="text-sm text-red-600">
            {serverError}
          </p>
        ) : null}

        <Button type="submit" fullWidth disabled={submit.isPending}>
          {submit.isPending ? 'submitting…' : 'submit request'}
        </Button>
      </form>
    </ContentContainer>
  );
}

function QuestionField({
  question,
  value,
  onChange,
  error,
}: {
  question: JoinQuestion;
  value: string;
  onChange: (v: string) => void;
  error?: string | undefined;
}) {
  const label = question.required ? question.label : `${question.label} (optional)`;
  if (question.fieldType === 'select') {
    return (
      <Select
        label={label}
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
        }}
        options={question.options.map((o) => ({ value: o, label: o }))}
        placeholder="select one"
        error={error}
      />
    );
  }
  if (isMultiline(question)) {
    return (
      <Textarea
        label={label}
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
        }}
        maxLength={MAX_ANSWER}
        rows={5}
        error={error}
      />
    );
  }
  return (
    <TextField
      label={label}
      value={value}
      onChange={(e) => {
        onChange(e.target.value);
      }}
      maxLength={MAX_ANSWER}
      error={error}
    />
  );
}

function extractError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return 'something went wrong — try again';
}
