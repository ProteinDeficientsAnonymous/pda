import { useState } from 'react';

import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { TextField } from '@/components/ui/TextField';
import { AvatarUpload } from '@/screens/settings/AvatarUpload';
import { InlineBirthday } from '@/screens/settings/InlineBirthday';
import { PrivacyToggles } from '@/screens/settings/PrivacyToggles';
import { extractApiError } from '@/utils/errors';

const MAX_BIO = 500;

interface Props {
  onDone: () => void;
}

export function OnboardingProfileStep({ onDone }: Props) {
  const user = useAuthStore((s) => s.user);
  const updateProfile = useAuthStore((s) => s.updateProfile);
  const [bio, setBio] = useState('');
  const [pronouns, setPronouns] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasPhoto = Boolean(user?.profilePhotoUrl);

  async function onFinish() {
    const trimmedBio = bio.trim();
    const trimmedPronouns = pronouns.trim();
    if (!trimmedBio && !trimmedPronouns) {
      onDone();
      return;
    }
    setError(null);
    setSaving(true);
    try {
      await updateProfile({
        ...(trimmedBio ? { bio: trimmedBio } : {}),
        ...(trimmedPronouns ? { pronouns: trimmedPronouns } : {}),
      });
      onDone();
    } catch (err) {
      setError(extractApiError(err, "couldn't save your profile — try again"));
    } finally {
      setSaving(false);
    }
  }

  if (!user) return null;

  return (
    <div className="flex flex-col gap-5">
      <p className="text-foreground-tertiary text-sm">
        totally optional — fill in what you want, skip the rest, change it later in settings
      </p>
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
        onSave={(v) => updateProfile({ birthday: v })}
        placeholder="add your birthday"
      />
      <div>
        <p className="text-foreground-tertiary mb-2 text-sm">privacy</p>
        <PrivacyToggles user={user} onChange={(patch) => void updateProfile(patch)} />
      </div>
      {error ? (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      ) : null}
      <Button type="button" fullWidth disabled={saving} onClick={() => void onFinish()}>
        {saving ? 'saving…' : 'done'}
      </Button>
      <button
        type="button"
        onClick={onDone}
        disabled={saving}
        className="text-foreground-tertiary hover:text-foreground focus-visible:ring-brand-200 text-sm underline transition-colors focus-visible:ring-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
      >
        do this later
      </button>
    </div>
  );
}
