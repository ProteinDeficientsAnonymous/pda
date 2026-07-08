import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { extractApiError } from '@/utils/errors';

import { AuthLayout } from './AuthLayout';

// Guidelines-consent gate. Modeled on OnboardingScreen — same AuthLayout shell.
// Blocks login completion: the only ways forward are to accept (clears
// needsGuidelinesConsent) or "not now", which logs out and returns to the
// landing page. Reached via OnboardingGate redirecting consent-pending users
// here; that gate pins them to /consent (except /guidelines, so they can read
// what they're agreeing to) until one of those two happens.
export default function ConsentScreen() {
  const acceptGuidelines = useAuthStore((s) => s.acceptGuidelines);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const [consented, setConsented] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onAccept() {
    if (!consented) return;
    setServerError(null);
    setSubmitting(true);
    try {
      await acceptGuidelines();
      void navigate('/calendar', { replace: true });
    } catch (err) {
      setServerError(extractApiError(err, "couldn't save your consent — try again"));
      setSubmitting(false);
    }
  }

  async function onSkip() {
    // Decline for now: drop the session and return to the landing page logged
    // out. No half-authed state — the only way into the app is to accept.
    setSubmitting(true);
    await logout();
    void navigate('/', { replace: true });
  }

  return (
    <AuthLayout
      title="before you continue"
      subtitle="we've updated our community guidelines — please read and agree to keep going"
    >
      <div className="flex flex-col gap-4">
        <label className="text-foreground flex items-start gap-2 text-sm leading-relaxed">
          <input
            type="checkbox"
            checked={consented}
            onChange={(e) => {
              setConsented(e.target.checked);
            }}
            className="mt-1"
          />
          <span>
            i have read and agree to the{' '}
            <Link to="/guidelines" target="_blank" className="text-brand-700 underline">
              community guidelines
            </Link>{' '}
            and community agreements
          </span>
        </label>
        {serverError ? (
          <p role="alert" className="text-destructive text-sm">
            {serverError}
          </p>
        ) : null}
        <Button
          type="button"
          fullWidth
          disabled={!consented || submitting}
          onClick={() => void onAccept()}
        >
          {submitting ? 'saving…' : 'continue'}
        </Button>
        <button
          type="button"
          disabled={submitting}
          onClick={() => void onSkip()}
          className="text-foreground-tertiary text-center text-sm underline disabled:opacity-50"
        >
          not now
        </button>
      </div>
    </AuthLayout>
  );
}
