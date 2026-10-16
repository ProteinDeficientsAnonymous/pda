import { useRef, useState } from 'react';

import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { TextField } from '@/components/ui/TextField';
import type { ConsentTypeValue } from '@/models/consent';
import { AvatarUpload } from '@/screens/settings/AvatarUpload';
import {
  type DateDraft,
  InlineBirthday,
  InlineVeganniversary,
} from '@/screens/settings/InlineBirthday';
import { PrivacyToggles } from '@/screens/settings/PrivacyToggles';
import { extractApiError } from '@/utils/errors';

import { ConsentChecklist } from './ConsentChecklist';
import { useConsentChecklist } from './useConsentChecklist';

const MAX_BIO = 500;

function completeDraft(draft: DateDraft | null) {
  if (draft?.month == null || draft.year == null) return undefined;
  return { month: draft.month, day: draft.day, year: draft.year };
}

interface Props {
  onDone: () => void;
}

export function OnboardingProfileStep({ onDone }: Props) {
  const user = useAuthStore((s) => s.user);
  const updateProfile = useAuthStore((s) => s.updateProfile);
  const acceptConsents = useAuthStore((s) => s.acceptConsents);
  const [bio, setBio] = useState('');
  const [pronouns, setPronouns] = useState('');
  const [draft, setDraft] = useState<DateDraft | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { consents, checked, toggle, allChecked } = useConsentChecklist(user);
  const consentFlight = useRef<Promise<void> | null>(null);
  const [consentSaved, setConsentSaved] = useState(consents.length === 0);

  const hasPhoto = Boolean(user?.profilePhotoUrl);
  const canFinish = allChecked && consentSaved;

  function onToggle(type: ConsentTypeValue, isChecked: boolean) {
    toggle(type, isChecked);
    const next = new Set(checked);
    if (isChecked) next.add(type);
    else next.delete(type);
    if (!consents.every((c) => next.has(c.type)) || consentFlight.current) return;
    // One accept before profile saves: PATCH /me/ 403s until guidelines consent is stamped.
    consentFlight.current = acceptConsents(consents.map((c) => c.type))
      .then(() => {
        setConsentSaved(true);
      })
      .catch((err: unknown) => {
        consentFlight.current = null;
        setError(extractApiError(err, "couldn't save your consent — try again"));
      });
  }

  async function finish(extra: { bio?: string; pronouns?: string } = {}) {
    if (!canFinish) return;
    setError(null);
    setSaving(true);
    try {
      const veganniversary = completeDraft(draft);
      await updateProfile({
        ...extra,
        hasSeenVeganniversary: true,
        ...(veganniversary ? { veganniversary } : {}),
      });
      onDone();
    } catch (err) {
      setError(extractApiError(err, "couldn't save your profile — try again"));
    } finally {
      setSaving(false);
    }
  }

  async function onFinish() {
    const trimmedBio = bio.trim();
    const trimmedPronouns = pronouns.trim();
    await finish({
      ...(trimmedBio ? { bio: trimmedBio } : {}),
      ...(trimmedPronouns ? { pronouns: trimmedPronouns } : {}),
    });
  }

  if (!user) return null;

  return (
    <div className="flex flex-col gap-5">
      <p className="text-foreground-tertiary text-sm">
        totally optional — fill in what you want, skip the rest, change it later in settings
      </p>
      <ConsentChecklist consents={consents} checked={checked} onToggle={onToggle} />
      <fieldset
        disabled={!consentSaved}
        className="m-0 flex min-w-0 flex-col gap-5 border-0 p-0 disabled:opacity-60"
      >
        <div className="flex flex-col items-center gap-2">
          <AvatarUpload size="lg" />
          {hasPhoto ? <p className="text-foreground-tertiary text-sm">✓ photo added</p> : null}
        </div>
        <Textarea
          label="bio"
          value={bio}
          onChange={(e) => {
            setBio(e.target.value);
          }}
          maxLength={MAX_BIO}
          rows={4}
          hint="optional — a sentence or two about you"
        />
        <TextField
          label="pronouns (optional)"
          placeholder="e.g. she/her, they/them"
          value={pronouns}
          onChange={(e) => {
            setPronouns(e.target.value);
          }}
        />
        <InlineBirthday
          label="birthday"
          value={user.birthday}
          onSave={(v) =>
            updateProfile({
              birthday: v?.day != null ? { month: v.month, day: v.day, year: v.year } : null,
            })
          }
          placeholder="add your birthday"
        />
        <InlineVeganniversary
          value={user.veganniversary}
          onSave={(veganniversary) => updateProfile({ veganniversary })}
          onDraftChange={setDraft}
        />
        <div>
          <p className="text-foreground-tertiary mb-2 text-sm">privacy</p>
          <PrivacyToggles user={user} onChange={(patch) => void updateProfile(patch)} />
        </div>
      </fieldset>
      {error ? (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      ) : null}
      <Button
        type="button"
        fullWidth
        disabled={saving || !canFinish}
        onClick={() => void onFinish()}
      >
        {saving ? 'saving…' : 'done'}
      </Button>
      <button
        type="button"
        onClick={() => void finish()}
        disabled={saving || !canFinish}
        className="text-foreground-tertiary hover:text-foreground focus-visible:ring-brand-200 text-sm underline transition-colors focus-visible:ring-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
      >
        do this later
      </button>
    </div>
  );
}
