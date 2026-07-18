import { type SyntheticEvent, useState } from 'react';
import { Link } from 'react-router-dom';

import { getApiStatus } from '@/api/apiErrors';
import { type PublicRsvpOut, useSubmitPublicRsvp } from '@/api/publicRsvp';
import { Button } from '@/components/ui/Button';
import { Honeypot } from '@/components/ui/Honeypot';
import { PhoneField } from '@/components/ui/PhoneField';
import { RsvpStatusPicker } from '@/components/ui/RsvpStatusPicker';
import { TextField } from '@/components/ui/TextField';
import { Toggle } from '@/components/ui/Toggle';
import { type Event, RSVP_STATUS_LABELS, type RsvpInputStatus, RsvpStatus } from '@/models/event';
import { optionalEmail } from '@/utils/validators';

import { type AlreadyRsvpdResult, PublicRsvpPhoneStep } from './PublicRsvpPhoneStep';

const MAX_NAME = 100;
const PUBLIC_RSVP_STATUSES: RsvpInputStatus[] = [RsvpStatus.Attending, RsvpStatus.Maybe];

interface Props {
  event: Event;
  onSuccess: (result: PublicRsvpOut) => void;
  onMember: () => void;
  onAlreadyRsvpd: (result: AlreadyRsvpdResult) => void;
}

interface SubmitError {
  text: string;
  showSignIn: boolean;
}

function messageForStatus(status: number | null): SubmitError {
  if (status === 409) {
    return { text: 'looks like you already have an account — sign in to rsvp', showSignIn: true };
  }
  if (status === 429) {
    return { text: "you're rsvping too fast — try again in a few minutes", showSignIn: false };
  }
  if (status === 404) {
    return { text: "this event isn't accepting public rsvps anymore — refresh", showSignIn: false };
  }
  return { text: 'something went wrong — try again', showSignIn: false };
}

function statusLabel(status: RsvpInputStatus): string {
  return RSVP_STATUS_LABELS.find((s) => s.status === status)?.label ?? status;
}

export function PublicRsvpForm({ event, onSuccess, onMember, onAlreadyRsvpd }: Props) {
  const submit = useSubmitPublicRsvp();
  const [status, setStatus] = useState<RsvpInputStatus | null>(null);
  const [phoneConfirmed, setPhoneConfirmed] = useState(false);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [hasPlusOne, setHasPlusOne] = useState(false);
  const [website, setWebsite] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<SubmitError | null>(null);

  function validate(): boolean {
    const next: Record<string, string> = {};
    if (!firstName.trim()) next.firstName = 'first name required';
    if (!email.trim()) next.email = 'email required';
    else if (optionalEmail(email)) next.email = 'not a valid email';
    if (!phone.trim()) next.phone = 'phone required';
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setSubmitError(null);
    if (!status || !validate()) return;
    try {
      const result = await submit.mutateAsync({
        eventId: event.id,
        payload: {
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          email: email.trim(),
          phone_number: phone.trim(),
          status,
          has_plus_one: hasPlusOne,
          website,
        },
      });
      onSuccess(result);
    } catch (err) {
      setSubmitError(messageForStatus(getApiStatus(err)));
    }
  }

  function renderStep() {
    if (status === null) {
      return (
        <RsvpStatusPicker value={status} onSelect={setStatus} statuses={PUBLIC_RSVP_STATUSES} />
      );
    }
    if (!phoneConfirmed) {
      return (
        <PublicRsvpPhoneStep
          eventId={event.id}
          onMember={onMember}
          onAlreadyRsvpd={onAlreadyRsvpd}
          onNew={(result) => {
            setPhone(result.phone);
            setPhoneConfirmed(true);
          }}
        />
      );
    }
    return (
      <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-4" noValidate>
        <Honeypot value={website} onChange={setWebsite} />

        <div className="flex items-center justify-between">
          <p className="text-foreground-secondary text-sm">
            rsvping as <span className="text-foreground font-medium">{statusLabel(status)}</span>
          </p>
          <button
            type="button"
            onClick={() => {
              setStatus(null);
              setPhoneConfirmed(false);
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

        {event.allowPlusOnes ? (
          <Toggle
            label="bring a +1"
            checked={hasPlusOne}
            onChange={setHasPlusOne}
            className="justify-start gap-2"
          />
        ) : null}

        <Button type="submit" disabled={submit.isPending} fullWidth>
          rsvp
        </Button>

        {submitError ? (
          <div role="alert" className="text-destructive text-sm">
            <p>{submitError.text}</p>
            {submitError.showSignIn ? (
              <Link to="/login" className="text-info hover:underline">
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
    <section aria-label="rsvp" className="border-border bg-surface mt-8 rounded-lg border p-6">
      <h2 className="mb-4 text-base font-medium">rsvp</h2>
      {renderStep()}
    </section>
  );
}
