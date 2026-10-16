import { useState } from 'react';

import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { type DateDraft, InlineVeganniversary } from '@/screens/settings/InlineBirthday';
import { VeganniversaryPrivacyToggles } from '@/screens/settings/PrivacyToggles';

function completeDraft(draft: DateDraft | null) {
  if (draft?.month == null || draft.year == null) return undefined;
  return { month: draft.month, day: draft.day, year: draft.year };
}

export function VeganniversaryPrompt() {
  const user = useAuthStore((s) => s.user);
  const updateProfile = useAuthStore((s) => s.updateProfile);
  const [draft, setDraft] = useState<DateDraft | null>(null);

  if (!user || user.hasSeenVeganniversary) return null;

  function dismiss() {
    const veganniversary = completeDraft(draft);
    void updateProfile({
      hasSeenVeganniversary: true,
      ...(veganniversary ? { veganniversary } : {}),
    });
  }

  return (
    <Dialog open onClose={dismiss} title="veganniversary">
      <div className="flex flex-col gap-4">
        <p className="text-foreground-tertiary text-sm">
          optional — when did you go vegan? you can change this later in settings.
        </p>
        <InlineVeganniversary
          value={user.veganniversary}
          onSave={(veganniversary) => updateProfile({ veganniversary })}
          onDraftChange={setDraft}
        />
        <VeganniversaryPrivacyToggles user={user} onChange={(patch) => void updateProfile(patch)} />
        <Button type="button" fullWidth onClick={dismiss}>
          done
        </Button>
      </div>
    </Dialog>
  );
}
