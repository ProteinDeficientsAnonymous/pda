import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { extractApiErrorOr } from '@/api/apiErrors';
import { AlreadyInvitedError, useJoinQuestions, useSubmitJoinRequest } from '@/api/join';
import type { JoinQuestion } from '@/api/join';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { PhoneField } from '@/components/ui/PhoneField';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { TextField } from '@/components/ui/TextField';
import { ContentContainer, ContentError, ContentLoading } from './ContentContainer';

// Mirrors backend FieldLimit constants.
const MAX_NAME = 64;
const MAX_ANSWER = 2000;

// Heuristic from join_screen.dart: multi-line if the label mentions "why".
function isMultiline(q: JoinQuestion): boolean {
  return q.fieldType === 'text' && q.label.toLowerCase().includes('why');
}

export default function JoinScreen() {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  if (isAuthed) return <AlreadyMemberPanel />;
  return <JoinFormLoader />;
}

function JoinFormLoader() {
  const { data: questions, isPending, isError } = useJoinQuestions();
  if (isPending) return <ContentLoading />;
  if (isError) {
    return <ContentError message="couldn't load the form — try refreshing" />;
  }
  return <JoinForm questions={questions} />;
}

function AlreadyMemberPanel() {
  const [copied, setCopied] = useState(false);
  const shareUrl = `${window.location.origin}/join`;

  async function copy() {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toast.success('link copied 🌱');
      window.setTimeout(() => {
        setCopied(false);
      }, 2000);
    } catch {
      toast.error("couldn't copy — try selecting the text");
    }
  }

  return (
    <ContentContainer>
      <h1 className="mb-2 text-2xl font-medium tracking-tight">you're already in 🌱</h1>
      <p className="text-foreground-tertiary mb-6 text-sm">
        want to bring a friend? send them this link —
      </p>
      <div className="flex flex-col gap-3">
        <input
          readOnly
          value={shareUrl}
          onFocus={(e) => {
            e.currentTarget.select();
          }}
          className="border-border bg-background w-full rounded-md border px-3 py-2 font-mono text-xs"
        />
        <Button variant="secondary" onClick={() => void copy()}>
          {copied ? 'copied ✓' : 'copy link'}
        </Button>
      </div>
    </ContentContainer>
  );
}

function JoinForm({ questions }: { questions: readonly JoinQuestion[] }) {
  const submit = useSubmitJoinRequest();
  const navigate = useNavigate();

  const [displayName, setDisplayName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [smsConsent, setSmsConsent] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  // Honeypot: real users never touch this. Bots auto-fill every input — when
  // the value reaches the server, the request is silently dropped.
  const [website, setWebsite] = useState('');

  function validate(): boolean {
    const next: Record<string, string> = {};
    if (!displayName.trim()) next.displayName = 'name required';
    else if (!/^[\p{L}\p{M}' \-.]+$/u.test(displayName)) next.displayName = 'letters only';
    if (!phoneNumber.trim()) next.phoneNumber = 'phone required';
    if (!smsConsent) next.smsConsent = 'please agree to receive sms about events';
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
        smsConsent,
        website,
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
      <p className="text-foreground-tertiary mb-6 text-sm">
        we review all requests — you'll hear from us once a vetting member has had a look
      </p>

      <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-4" noValidate>
        <div aria-hidden="true" className="absolute -left-[9999px] h-0 w-0 overflow-hidden">
          <label htmlFor="website-hp">website (leave blank)</label>
          <input
            id="website-hp"
            type="text"
            name="website"
            tabIndex={-1}
            autoComplete="off"
            value={website}
            onChange={(e) => {
              setWebsite(e.target.value);
            }}
          />
        </div>
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
        <PhoneField
          label="phone number"
          value={phoneNumber}
          onChange={setPhoneNumber}
          error={errors.phoneNumber}
          hint="use the number you use (or will use) to connect with the community"
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

        <label className="text-foreground flex items-start gap-2 text-sm leading-relaxed">
          <input
            type="checkbox"
            checked={smsConsent}
            onChange={(e) => {
              setSmsConsent(e.target.checked);
            }}
            className="mt-1"
            aria-describedby={errors.smsConsent ? 'sms-consent-error' : undefined}
          />
          <span>
            i agree to pda's{' '}
            <Link to="/sms-policy" target="_blank" className="text-brand-700 underline">
              sms policy
            </Link>{' '}
            — i may receive event-related text messages and can reply STOP to opt out.
          </span>
        </label>
        {errors.smsConsent ? (
          <p id="sms-consent-error" role="alert" className="text-destructive -mt-2 text-xs">
            {errors.smsConsent}
          </p>
        ) : null}

        {serverError ? (
          <p role="alert" className="text-destructive text-sm">
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
  return extractApiErrorOr(err, 'something went wrong — try again');
}
