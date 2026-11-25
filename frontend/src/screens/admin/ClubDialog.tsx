import type { SyntheticEvent } from 'react';
import { useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import type { Club } from '@/api/clubs';
import { useCreateClub, useUpdateClub } from '@/api/clubs';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Textarea } from '@/components/ui/Textarea';
import { TextField } from '@/components/ui/TextField';

interface Props {
  open: boolean;
  onClose: () => void;
  /** If set, the dialog is in edit mode. */
  existing?: Club | undefined;
}

export function ClubDialog(props: Props) {
  if (!props.open) return null;
  return <ClubDialogBody key={props.existing?.id ?? 'new'} {...props} />;
}

function ClubDialogBody({ open, onClose, existing }: Props) {
  const create = useCreateClub();
  const update = useUpdateClub(existing?.id ?? '');
  const busy = create.isPending || update.isPending;
  const [name, setName] = useState(existing?.name ?? '');
  const [requirements, setRequirements] = useState(existing?.requirements ?? '');
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError('name required');
      return;
    }
    const input = { name: name.trim(), requirements: requirements.trim() };
    try {
      if (existing) await update.mutateAsync(input);
      else await create.mutateAsync(input);
      onClose();
    } catch (err) {
      setError(extractApiErrorOr(err, "couldn't save — try again"));
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title={existing ? 'edit club' : 'add club'}>
      <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3">
        <TextField
          label="name"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
          }}
          maxLength={100}
        />
        <Textarea
          label="requirements"
          hint="who can join, shown on the join form (optional)"
          value={requirements}
          onChange={(e) => {
            setRequirements(e.target.value);
          }}
          rows={3}
        />
        {error ? (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        ) : null}
        <div className="mt-2 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose} disabled={busy} type="button">
            cancel
          </Button>
          <Button type="submit" disabled={busy}>
            {busy ? 'saving…' : 'save'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
