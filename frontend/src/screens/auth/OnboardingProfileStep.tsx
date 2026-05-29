import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { AvatarUpload } from '@/screens/settings/AvatarUpload';
import { useAuthStore } from '@/auth/store';
import { extractApiError } from '@/utils/errors';

const MAX_BIO = 500;

interface Props {
  onDone: () => void;
}

export function OnboardingProfileStep({ onDone }: Props) {
  const user = useAuthStore((s) => s.user);
  const updateProfile = useAuthStore((s) => s.updateProfile);
  const [bio, setBio] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasPhoto = Boolean(user?.profilePhotoUrl);

  async function onFinish() {
    const trimmed = bio.trim();
    if (!trimmed) {
      onDone();
      return;
    }
    setError(null);
    setSaving(true);
    try {
      await updateProfile({ bio: trimmed });
      onDone();
    } catch (err) {
      setError(extractApiError(err, "couldn't save your bio — try again"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
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
        className="text-foreground-tertiary hover:text-foreground text-sm underline transition-colors"
      >
        do this later
      </button>
    </div>
  );
}
