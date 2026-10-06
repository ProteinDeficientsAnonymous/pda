import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { TextField } from '@/components/ui/TextField';

const CONFIRM_WORD = 'delete';

export function DeleteAccountSection() {
  const deleteAccount = useAuthStore((s) => s.deleteAccount);
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function close() {
    setOpen(false);
    setTyped('');
    setError(null);
  }

  async function onDelete() {
    setDeleting(true);
    setError(null);
    try {
      await deleteAccount();
      void navigate('/', { replace: true });
    } catch (err) {
      setError(extractApiErrorOr(err, "couldn't delete your account — try again"));
      setDeleting(false);
    }
  }

  return (
    <>
      <p className="text-muted text-sm">
        deleting your account removes your access to the site. you'll also be removed from the pda
        whatsapp group.
      </p>
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
          <p>you'll lose access to the site immediately.</p>
          <p className="font-medium">
            you'll also be removed from the pda whatsapp group — we don't keep anyone in the
            whatsapp who isn't on the site.
          </p>
          <p>if you want to come back later, you'll need to submit a new join request.</p>
          <TextField
            label={`type "${CONFIRM_WORD}" to confirm`}
            value={typed}
            onChange={(e) => {
              setTyped(e.target.value);
            }}
            autoComplete="off"
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
            variant="secondary"
            className="text-destructive border-destructive"
            onClick={() => void onDelete()}
            disabled={deleting || typed.trim().toLowerCase() !== CONFIRM_WORD}
          >
            {deleting ? 'deleting…' : 'delete account'}
          </Button>
        </div>
      </Dialog>
    </>
  );
}
