import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { extractApiError } from '@/utils/errors';

import { AuthLayout } from './AuthLayout';
import { ConsentChecklist } from './ConsentChecklist';
import { useConsentChecklist } from './useConsentChecklist';

// standalone consent gate: accept every outstanding consent to continue, or "not now" to log out
export default function ConsentScreen() {
  const user = useAuthStore((s) => s.user);
  const acceptConsents = useAuthStore((s) => s.acceptConsents);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const { consents, checked, toggle, allChecked, acceptedTypes } = useConsentChecklist(user);
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onAccept() {
    if (!allChecked) return;
    setServerError(null);
    setSubmitting(true);
    try {
      await acceptConsents(acceptedTypes);
      void navigate('/calendar', { replace: true });
    } catch (err) {
      setServerError(extractApiError(err, "couldn't save your consent — try again"));
      setSubmitting(false);
    }
  }

  async function onSkip() {
    // decline: drop the session and return to the landing page logged out
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
        <ConsentChecklist consents={consents} checked={checked} onToggle={toggle} />
        {serverError ? (
          <p role="alert" className="text-destructive text-sm">
            {serverError}
          </p>
        ) : null}
        <Button
          type="button"
          fullWidth
          disabled={!allChecked || submitting}
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
