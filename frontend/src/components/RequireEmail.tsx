import { type SyntheticEvent, useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import { updateProfile } from '@/api/auth';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';

export function RequireEmail({ onSkip }: { onSkip: () => void }) {
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    const trimmed = email.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      setError('not a valid email');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const user = await updateProfile({ email: trimmed });
      // Push the updated user into the store so the gate stops rendering this modal.
      useAuthStore.setState({ user });
    } catch (err) {
      setError(extractApiErrorOr(err, "couldn't save your email — try again"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="require-email-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <div aria-hidden="true" className="absolute inset-0 bg-black/60" />
      <div className="bg-surface relative w-full max-w-sm rounded-lg p-6">
        <h2 id="require-email-title" className="mb-2 text-lg font-medium">
          add your email
        </h2>
        <p className="text-muted mb-4 text-sm">
          we use email for account recovery and event updates — add yours to stay logged in, or
          keep browsing logged out
        </p>
        <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3" noValidate>
          <TextField
            label="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
            }}
            error={error ?? undefined}
            required
          />
          <Button type="submit" fullWidth disabled={submitting}>
            {submitting ? 'saving…' : 'save'}
          </Button>
          <Button type="button" variant="ghost" fullWidth onClick={onSkip} disabled={submitting}>
            not now
          </Button>
        </form>
      </div>
    </div>
  );
}
