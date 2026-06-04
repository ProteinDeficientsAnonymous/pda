import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthLayout } from './AuthLayout';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/auth/store';
import { extractApiError } from '@/utils/errors';

// Hard guidelines-consent gate. Modeled on OnboardingScreen — same AuthLayout
// shell, single blocking action, no skip or dismiss. Reached only via
// OnboardingGate redirecting consent-pending users to /consent; the gate pins
// them here until acceptGuidelines() clears needsGuidelinesConsent.
export default function ConsentScreen() {
  const acceptGuidelines = useAuthStore((s) => s.acceptGuidelines);
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
      </div>
    </AuthLayout>
  );
}
