import { type SyntheticEvent, useState } from 'react';

import { useResendPublicRsvpManageLink } from '@/api/publicRsvp';
import { Button } from '@/components/ui/Button';
import { PhoneField } from '@/components/ui/PhoneField';
import { TextField } from '@/components/ui/TextField';
import { extractApiError } from '@/utils/errors';

export function ResendManageLinkForm() {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [error, setError] = useState<string | undefined>(undefined);
  const resend = useResendPublicRsvpManageLink();

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => {
          setOpen(true);
        }}
        className="text-foreground-secondary mt-4 text-sm underline underline-offset-2"
      >
        lost your link?
      </button>
    );
  }

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setError(undefined);
    try {
      await resend.mutateAsync({ email, phoneNumber: phone });
    } catch (err) {
      setError(extractApiError(err, "couldn't send that — try again").toLowerCase());
    }
  }

  if (resend.isSuccess) {
    return <p className="text-foreground-secondary mt-4 text-sm">{resend.data.detail}</p>;
  }

  return (
    <form
      onSubmit={(e) => void onSubmit(e)}
      className="border-border-strong mt-4 flex flex-col gap-3 border-t pt-4"
      noValidate
    >
      <p className="text-foreground-secondary text-sm">
        lost your link? enter your phone + email and we'll resend it
      </p>
      <PhoneField label="phone number" value={phone} onChange={setPhone} />
      <TextField
        label="email"
        type="email"
        value={email}
        onChange={(e) => {
          setEmail(e.target.value);
        }}
        error={error}
        required
      />
      <Button type="submit" disabled={resend.isPending} fullWidth>
        {resend.isPending ? 'sending…' : 'resend my link'}
      </Button>
    </form>
  );
}
