import { useState } from 'react';
import { isAxiosError } from 'axios';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { TextField } from '@/components/ui/TextField';
import { useAuthStore } from '@/auth/store';
import { passwordRule } from '@/screens/auth/passwordRule';
import { PasswordChecklist } from '@/screens/auth/PasswordChecklist';

interface Props {
  open: boolean;
  onClose: () => void;
}

export function ChangePasswordDialog({ open, onClose }: Props) {
  const changePassword = useAuthStore((s) => s.changePassword);
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setCurrent('');
    setNext('');
    setConfirm('');
    setError(null);
  }

  async function save() {
    setError(null);
    const parsed = passwordRule.safeParse(next);
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? 'invalid password');
      return;
    }
    if (next !== confirm) {
      setError("passwords don't match");
      return;
    }
    if (next === current) {
      setError('new password must differ from current');
      return;
    }
    setSaving(true);
    try {
      await changePassword(current, next);
      reset();
      onClose();
    } catch (err) {
      setError(extractError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={() => {
        reset();
        onClose();
      }}
      title="change password"
    >
      <div className="flex flex-col gap-3">
        <TextField
          label="current password"
          type="password"
          value={current}
          onChange={(e) => {
            setCurrent(e.target.value);
          }}
          autoComplete="current-password"
          maxLength={72}
        />
        <PasswordChecklist value={next} />
        <TextField
          label="new password"
          type="password"
          value={next}
          onChange={(e) => {
            setNext(e.target.value);
          }}
          autoComplete="new-password"
          maxLength={72}
        />
        <TextField
          label="confirm new password"
          type="password"
          value={confirm}
          onChange={(e) => {
            setConfirm(e.target.value);
          }}
          autoComplete="new-password"
          maxLength={72}
        />
      </div>
      {error ? (
        <p role="alert" className="mt-3 text-sm text-red-600">
          {error}
        </p>
      ) : null}
      <div className="mt-4 flex justify-end gap-2">
        <Button
          variant="ghost"
          onClick={() => {
            reset();
            onClose();
          }}
          disabled={saving}
        >
          cancel
        </Button>
        <Button onClick={() => void save()} disabled={saving}>
          {saving ? 'saving…' : 'update password'}
        </Button>
      </div>
    </Dialog>
  );
}

function extractError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't update password — try again";
}
