import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { PasswordField } from '@/components/ui/PasswordField';

export function DeleteAccountSection() {
  const deleteAccount = useAuthStore((s) => s.deleteAccount);
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function close() {
    if (deleting) return;
    setOpen(false);
    setPassword('');
    setError(null);
  }

  async function onDelete() {
    setDeleting(true);
    setError(null);
    try {
      await deleteAccount(password);
      void navigate('/', { replace: true });
    } catch (err) {
      setError(extractApiErrorOr(err, "couldn't delete your account — try again"));
      setDeleting(false);
    }
  }

  return (
    <>
      <div>
        <Button
          variant="secondary"
          onClick={() => {
            setOpen(true);
          }}
        >
          delete my account
        </Button>
      </div>
      <Dialog open={open} onClose={close} title="delete your account?">
        <div className="flex flex-col gap-3 text-sm">
          <p className="font-medium">
            you'll lose access right away and your upcoming rsvps are released — an admin will
            remove you from the pda whatsapp group.
          </p>
          <p>
            you'll step down as co-host on events that have another host — events you host alone
            stay listed under you, so hand them off first.
          </p>
          <p>
            your profile is hidden, not erased. ask an admin if you want your data removed, or send
            a new join request to come back.
          </p>
          <PasswordField
            label="enter your password to confirm"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
            }}
            autoComplete="current-password"
            maxLength={72}
          />
        </div>
        {error ? (
          <p role="alert" className="text-destructive mt-3 text-sm">
            {error}
          </p>
        ) : null}
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={close} disabled={deleting}>
            cancel
          </Button>
          <Button
            variant="destructive"
            onClick={() => void onDelete()}
            disabled={deleting || !password}
          >
            {deleting ? 'deleting…' : 'delete account'}
          </Button>
        </div>
      </Dialog>
    </>
  );
}
