import { useEffect, useRef, useState } from 'react';
import { isValidPhoneNumber } from 'react-phone-number-input';
import { Link, useNavigate } from 'react-router-dom';

import { extractApiErrorOr, getApiStatus, hasErrorCode } from '@/api/apiErrors';
import { type PublicRsvpOut, useSubmitPublicRsvp } from '@/api/publicRsvp';
import { Code } from '@/api/validationCodes.gen';
import { Button } from '@/components/ui/Button';
import { Honeypot } from '@/components/ui/Honeypot';
import { PhoneField } from '@/components/ui/PhoneField';
import { RsvpStatusPicker } from '@/components/ui/RsvpStatusPicker';
import { TextField } from '@/components/ui/TextField';
import {
  type Event,
  eventPath,
  RSVP_STATUS_LABELS,
  type RsvpInputStatus,
  RsvpStatus,
  spotsLeft,
} from '@/models/event';
import {
  optionalEmail,
  optionalPersonName,
  personName,
  ValidationMessage,
} from '@/utils/validators';

import { PaymentConfirmStep } from './PaymentConfirmStep';
import { PublicRsvpPhoneStep } from './PublicRsvpPhoneStep';
import { RsvpCommentField } from './RsvpCommentField';
import { RsvpQuestionFields } from './RsvpQuestionFields';
import { missingRequiredQuestionIds, type RsvpAnswerValue } from './rsvpQuestions';
import { usePaymentGate } from './usePaymentGate';

const MAX_NAME = 100;
const PUBLIC_RSVP_STATUSES: RsvpInputStatus[] = [RsvpStatus.Attending, RsvpStatus.Maybe];

interface Props {
  event: Event;
  onSuccess: (result: PublicRsvpOut) => void;
}

interface SubmitError {
  text: string;
  showSignIn: boolean;
}

function messageForStatus(status: number | null, err: unknown): SubmitError {
  if (hasErrorCode(err, Code.Event.PaymentConfirmationRequired)) {
    return { text: extractApiErrorOr(err, 'confirm you paid before rsvping'), showSignIn: false };
  }
  if (hasErrorCode(err, Code.Event.RsvpCouldNotBeCreated)) {
    return {
      text: "we couldn't set up your rsvp with those details — reach out and we'll help",
      showSignIn: false,
    };
  }
  if (hasErrorCode(err, Code.Auth.AccountArchived)) {
    return {
      text: "we couldn't set up your rsvp — reach out and we'll help",
      showSignIn: false,
    };
  }
  if (status === 409) {
    return { text: 'looks like you already have an account — sign in to rsvp', showSignIn: true };
  }
  if (status === 429) {
    return { text: "you're rsvping too fast — try again in a few minutes", showSignIn: false };
  }
  if (status === 404) {
    return { text: "this event isn't accepting public rsvps anymore — refresh", showSignIn: false };
  }
  return { text: extractApiErrorOr(err, 'something went wrong — try again'), showSignIn: false };
}

function statusLabel(status: RsvpInputStatus, atCapacity: boolean): string {
  if (status === RsvpStatus.Attending && atCapacity) return 'join the waitlist';
  return RSVP_STATUS_LABELS.find((s) => s.status === status)?.label ?? status;
}

export function PublicRsvpForm({ event, onSuccess }: Props) {
  const submit = useSubmitPublicRsvp();
  const navigate = useNavigate();
  const atCapacity = spotsLeft(event) === 0;
  const questions = event.rsvpQuestions;
  const [status, setStatus] = useState<RsvpInputStatus | null>(null);
  const [phoneConfirmed, setPhoneConfirmed] = useState(false);
  const [isNonMember, setIsNonMember] = useState(false);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [comment, setComment] = useState('');
  const [website, setWebsite] = useState('');
  const [answers, setAnswers] = useState<Record<string, RsvpAnswerValue | undefined>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<SubmitError | null>(null);
  const [showPayment, setShowPayment] = useState(false);
  const submitErrorRef = useRef<HTMLDivElement | null>(null);
  const needsPaymentFor = usePaymentGate(event);

  useEffect(() => {
    if (!submitError) return;
    submitErrorRef.current?.scrollIntoView({ block: 'center' });
    submitErrorRef.current?.focus();
  }, [submitError]);

  function validate(): boolean {
    const next: Record<string, string> = {};
    const firstNameErr = personName(firstName);
    if (firstNameErr)
      next.firstName =
        firstNameErr === ValidationMessage.REQUIRED ? 'first name required' : firstNameErr;
    const lastNameErr = optionalPersonName(lastName);
    if (lastNameErr) next.lastName = lastNameErr;
    if (!email.trim()) next.email = 'email required';
    else if (optionalEmail(email)) next.email = 'not a valid email';
    if (!phone.trim()) next.phone = 'phone required';
    else if (!isValidPhoneNumber(phone)) next.phone = 'invalid phone number';
    for (const id of missingRequiredQuestionIds(questions, answers)) {
      next[id] = 'required';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function onSubmit(paidConfirmed: boolean) {
    setSubmitError(null);
    if (!status || !validate()) return;
    const filledAnswers: Record<string, string> = {};
    for (const q of questions) {
      const value = answers[q.id];
      if (value?.trim()) filledAnswers[q.id] = value;
    }
    try {
      const result = await submit.mutateAsync({
        eventId: event.id,
        payload: {
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          email: email.trim(),
          phone_number: phone.trim(),
          status,
          has_plus_one: false,
          comment: comment.trim() || null,
          questionnaire_responses: filledAnswers,
          website,
          paid_confirmed: paidConfirmed,
        },
      });
      onSuccess(result);
    } catch (err) {
      setSubmitError(messageForStatus(getApiStatus(err), err));
    }
  }

  function handleSubmitClick() {
    if (!status || !validate()) return;
    if (needsPaymentFor(status)) {
      setShowPayment(true);
      return;
    }
    void onSubmit(false);
  }

  function renderStep() {
    if (status === null) {
      return (
        <RsvpStatusPicker
          value={status}
          onSelect={setStatus}
          statuses={PUBLIC_RSVP_STATUSES}
          labelFor={(s, defaultLabel) =>
            s === RsvpStatus.Attending && atCapacity ? 'join the waitlist' : defaultLabel
          }
        />
      );
    }
    if (isNonMember) {
      return (
        <div className="flex flex-col gap-2">
          <p className="text-foreground-secondary text-sm">
            we recognized your number — check your email for a link to manage your rsvp
          </p>
          <button
            type="button"
            onClick={() => {
              setIsNonMember(false);
              setPhoneConfirmed(false);
            }}
            className="text-info self-start text-sm hover:underline"
          >
            use a different number
          </button>
        </div>
      );
    }
    if (!phoneConfirmed) {
      return (
        <PublicRsvpPhoneStep
          eventId={event.id}
          onMember={(memberPhone) => {
            void navigate('/login', {
              state: { phone: memberPhone, redirect: eventPath(event) },
            });
          }}
          onNonMember={() => {
            setIsNonMember(true);
          }}
          onNew={(result) => {
            setPhone(result.phone);
            setPhoneConfirmed(true);
          }}
        />
      );
    }
    if (showPayment) {
      return (
        <PaymentConfirmStep
          event={event}
          busy={submit.isPending}
          onConfirm={() => {
            void onSubmit(true);
          }}
          onBack={() => {
            setShowPayment(false);
          }}
        />
      );
    }
    return (
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSubmitClick();
        }}
        className="flex flex-col gap-4"
        noValidate
      >
        <Honeypot value={website} onChange={setWebsite} />

        <div className="flex items-center justify-between">
          <p className="text-foreground-secondary text-sm">
            rsvping as{' '}
            <span className="text-foreground font-medium">{statusLabel(status, atCapacity)}</span>
          </p>
          <button
            type="button"
            onClick={() => {
              setStatus(null);
            }}
            className="text-info text-sm hover:underline"
          >
            change
          </button>
        </div>

        <TextField
          label="first name"
          value={firstName}
          onChange={(e) => {
            setFirstName(e.target.value);
          }}
          maxLength={MAX_NAME}
          autoComplete="given-name"
          error={errors.firstName}
          required
        />
        <TextField
          label="last name"
          value={lastName}
          onChange={(e) => {
            setLastName(e.target.value);
          }}
          maxLength={MAX_NAME}
          autoComplete="family-name"
          error={errors.lastName}
        />
        <TextField
          label="email"
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
          }}
          autoComplete="email"
          error={errors.email}
          required
        />
        <PhoneField label="phone" value={phone} onChange={setPhone} error={errors.phone} />

        <RsvpQuestionFields
          questions={questions}
          answers={answers}
          onChange={(id, value) => {
            setAnswers((prev) => ({ ...prev, [id]: value }));
            setErrors((prev) => {
              if (!(id in prev)) return prev;
              const { [id]: _removed, ...rest } = prev;
              return rest;
            });
          }}
          errors={errors}
          disabled={submit.isPending}
        />

        <RsvpCommentField
          value={comment}
          onChange={setComment}
          disabled={submit.isPending}
          onSubmitShortcut={handleSubmitClick}
        />

        <Button type="submit" disabled={submit.isPending} fullWidth>
          rsvp
        </Button>

        {submitError ? (
          <div role="alert" tabIndex={-1} ref={submitErrorRef} className="text-destructive text-sm">
            <p>{submitError.text}</p>
            {submitError.showSignIn ? (
              <Link
                to={`/login?redirect=${encodeURIComponent(eventPath(event))}`}
                className="text-info hover:underline"
              >
                sign in
              </Link>
            ) : null}
          </div>
        ) : null}

        <p className="text-foreground-tertiary text-xs">
          rsvping doesn't make you a pda member —{' '}
          <Link to="/join" className="text-info hover:underline">
            request to join
          </Link>
        </p>
      </form>
    );
  }

  return (
    <section aria-label="rsvp" className="border-border bg-surface rounded-lg border p-6">
      <h2 className="mb-4 text-base font-medium">rsvp</h2>
      <p className="text-foreground-tertiary mb-4 text-sm">
        rsvp to see the location and more details
      </p>
      {renderStep()}
    </section>
  );
}
