import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { ConsentType } from '@/models/consent';
import { extractApiError } from '@/utils/errors';

import { AuthLayout } from './AuthLayout';
import { ConsentChecklist } from './ConsentChecklist';
import { ContactPrivacyStep } from './ContactPrivacyStep';
import { useConsentChecklist } from './useConsentChecklist';

// standalone consent gate: accept every outstanding consent to continue, or "not now" to log out
export default function ConsentScreen() {
  const user = useAuthStore((s) => s.user);
  const acceptConsents = useAuthStore((s) => s.acceptConsents);
  const updateProfile = useAuthStore((s) => s.updateProfile);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const { consents, checked, toggle, allChecked, acceptedTypes } = useConsentChecklist(user);
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const needsContactPrivacyStep = user?.needsContactPrivacyConsent ?? false;
  const [showPhone, setShowPhone] = useState(user?.showPhone ?? true);
  const [showEmail, setShowEmail] = useState(user?.showEmail ?? true);

  async function onAccept() {
    if (!allChecked) return;
    setServerError(null);
    setSubmitting(true);
    try {
      if (needsContactPrivacyStep) {
        await updateProfile({ showPhone, showEmail });
      }
      const consentTypes = needsContactPrivacyStep
        ? [...acceptedTypes, ConsentType.ContactPrivacy]
        : acceptedTypes;
      await acceptConsents(consentTypes);
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

  const subtitle =
    consents.length > 0
      ? "we've updated our community guidelines — please read and agree to keep going"
      : 'a quick privacy check before you continue';

  return (
    <AuthLayout title="before you continue" subtitle={subtitle}>
      <div className="flex flex-col gap-4">
        <ConsentChecklist consents={consents} checked={checked} onToggle={toggle} />
        {needsContactPrivacyStep ? (
          <ContactPrivacyStep
            showPhone={showPhone}
            showEmail={showEmail}
            onChange={(patch) => {
              if (patch.showPhone !== undefined) setShowPhone(patch.showPhone);
              if (patch.showEmail !== undefined) setShowEmail(patch.showEmail);
            }}
          />
        ) : null}
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
        <Button
          type="button"
          variant="ghost"
          fullWidth
          disabled={submitting}
          onClick={() => void onSkip()}
        >
          not now
        </Button>
      </div>
    </AuthLayout>
  );
}
