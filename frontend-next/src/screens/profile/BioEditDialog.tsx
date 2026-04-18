import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Textarea } from '@/components/ui/Textarea';
import { useAuthStore } from '@/auth/store';

const MAX_BIO = 500;

interface Props {
  open: boolean;
  initialValue: string;
  onClose: () => void;
}

export function BioEditDialog({ open, initialValue, onClose }: Props) {
  const updateProfile = useAuthStore((s) => s.updateProfile);
  const [value, setValue] = useState(initialValue);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await updateProfile({ bio: value.trim() });
      onClose();
    } catch {
      setError("couldn't save bio — try again");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="edit bio">
      <Textarea
        label="bio"
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
        }}
        maxLength={MAX_BIO}
        rows={5}
      />
      {error ? (
        <p role="alert" className="mt-2 text-sm text-red-600">
          {error}
        </p>
      ) : null}
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose} disabled={saving}>
          cancel
        </Button>
        <Button onClick={() => void save()} disabled={saving}>
          {saving ? 'saving…' : 'save'}
        </Button>
      </div>
    </Dialog>
  );
}
