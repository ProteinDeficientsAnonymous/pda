import type { SyntheticEvent } from 'react';
import { useEffect, useState } from 'react';
import { isValidPhoneNumber } from 'react-phone-number-input';

import { type RequestLoginLinkDelivery, useRequestLoginLink } from '@/api/auth';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { PhoneField } from '@/components/ui/PhoneField';
import { extractApiError } from '@/utils/errors';

function formatCountdown(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes.toString()}:${seconds.toString().padStart(2, '0')}`;
}

interface Props {
  open: boolean;
  initialPhone?: string;
  onClose: () => void;
}

// Outer wrapper unmounts the form on close so internal state (phone, error, sent)
// is reseeded from `initialPhone` each time the dialog opens — no effect-based
// state syncing required.
export function RequestLoginLinkDialog({ open, initialPhone, onClose }: Props) {
  if (!open) return null;
  return <RequestLoginLinkForm initialPhone={initialPhone ?? ''} onClose={onClose} />;
}

function RequestLoginLinkForm({
  initialPhone,
  onClose,
}: {
  initialPhone: string;
  onClose: () => void;
}) {
  const [phone, setPhone] = useState(initialPhone);
  const [error, setError] = useState<string | null>(null);
  const [delivery, setDelivery] = useState<RequestLoginLinkDelivery | null>(null);
  const [retryAfter, setRetryAfter] = useState<number | null>(null);
  const requestLink = useRequestLoginLink();

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setError(null);
    if (!phone || !isValidPhoneNumber(phone)) {
      setError('enter a valid phone number');
      return;
    }
    try {
      const result = await requestLink.mutateAsync(phone);
      setDelivery(result.delivery);
      setRetryAfter(result.retryAfterSeconds);
    } catch (err) {
      const message = extractApiError(err, "couldn't send the request — try again");
      setError(message);
    }
  }

  if (delivery === 'cooldown') {
    return <CooldownResult initialSeconds={retryAfter} onClose={onClose} />;
  }

  if (delivery !== null) {
    const messages: Record<Exclude<RequestLoginLinkDelivery, 'cooldown'>, string> = {
      email:
        "if there's an account for that number, we sent a login link to the email on file — check your inbox, including spam 🌱",
      admin:
        "if there's an account for that number, an admin will follow up with your login link — sit tight 🌱",
    };
    const message = messages[delivery];
    return (
      <Dialog open onClose={onClose} title="request a login link">
        <div className="flex flex-col gap-4">
          <p className="text-muted text-sm">{message}</p>
          <div className="flex justify-end">
            <Button type="button" onClick={onClose}>
              done
            </Button>
          </div>
        </div>
      </Dialog>
    );
  }

  return (
    <Dialog open onClose={onClose} title="request a login link">
      <form
        onSubmit={(e) => {
          void onSubmit(e);
        }}
        className="flex flex-col gap-4"
      >
        <p className="text-muted text-sm">
          enter your phone number and we'll send a one-tap login link to the email on file
        </p>
        <PhoneField
          label="phone number"
          value={phone}
          onChange={setPhone}
          error={error ?? undefined}
        />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose} disabled={requestLink.isPending}>
            cancel
          </Button>
          <Button type="submit" disabled={requestLink.isPending}>
            {requestLink.isPending ? 'requesting…' : 'request link'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function CooldownResult({
  initialSeconds,
  onClose,
}: {
  initialSeconds: number | null;
  onClose: () => void;
}) {
  const [remaining, setRemaining] = useState(initialSeconds ?? 0);

  useEffect(() => {
    if (remaining <= 0) return;
    const id = window.setInterval(() => {
      setRemaining((s) => Math.max(0, s - 1));
    }, 1000);
    return () => {
      window.clearInterval(id);
    };
  }, [remaining]);

  return (
    <Dialog open onClose={onClose} title="request a login link">
      <div className="flex flex-col gap-4">
        <div
          role="alert"
          className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200"
        >
          <p>
            we didn't send a new link — you requested one just a moment ago, and it's still valid.
            check your inbox, including spam.
          </p>
          {remaining > 0 ? (
            <p className="mt-1 font-medium">try again in {formatCountdown(remaining)}</p>
          ) : (
            <p className="mt-1 font-medium">you can request another link now</p>
          )}
        </div>
        <div className="flex justify-end">
          <Button type="button" onClick={onClose}>
            done
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
