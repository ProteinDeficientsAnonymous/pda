import { type SyntheticEvent, useState } from 'react';
import { isValidPhoneNumber } from 'react-phone-number-input';

import { useCheckPublicRsvpPhone } from '@/api/publicRsvp';
import { Button } from '@/components/ui/Button';
import { PhoneField } from '@/components/ui/PhoneField';
import { extractApiError } from '@/utils/errors';

export interface PhoneStepResult {
  phone: string;
  status: 'new';
}

export interface AlreadyRsvpdResult {
  rsvpToken: string;
}

interface Props {
  onNew: (result: PhoneStepResult) => void;
  onMember: () => void;
  onAlreadyRsvpd: (result: AlreadyRsvpdResult) => void;
  onRecognized: () => void;
  eventId: string;
}

export function PublicRsvpPhoneStep({
  onNew,
  onMember,
  onAlreadyRsvpd,
  onRecognized,
  eventId,
}: Props) {
  const check = useCheckPublicRsvpPhone();
  const [phone, setPhone] = useState('');
  const [error, setError] = useState<string | undefined>(undefined);

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setError(undefined);
    if (!phone || !isValidPhoneNumber(phone)) {
      setError('enter a valid phone number');
      return;
    }
    try {
      const result = await check.mutateAsync({ eventId, phoneNumber: phone });
      if (result.status === 'member') {
        onMember();
        return;
      }
      if (result.status === 'already_rsvpd') {
        onAlreadyRsvpd({ rsvpToken: result.rsvp_token });
        return;
      }
      if (result.status === 'recognized') {
        onRecognized();
        return;
      }
      onNew({ phone, status: 'new' });
    } catch (err) {
      setError(extractApiError(err, "couldn't check your number — try again"));
    }
  }

  return (
    <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-4" noValidate>
      <p className="text-foreground-secondary text-sm">enter your phone number to continue</p>
      <PhoneField label="phone number" value={phone} onChange={setPhone} error={error} />
      <Button type="submit" disabled={check.isPending} fullWidth>
        {check.isPending ? 'checking…' : 'continue'}
      </Button>
    </form>
  );
}
