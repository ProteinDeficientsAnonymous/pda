import type { SyntheticEvent } from 'react';
import { useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import type { Club } from '@/api/clubs';
import { useClubReps, useCreateClub, useSetClubReps, useUpdateClub } from '@/api/clubs';
import type { MemberSearchResult } from '@/api/userSearch';
import { MemberPicker } from '@/components/MemberPicker';
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
  return <ClubDialogGate {...props} />;
}

function ClubDialogGate(props: Props) {
  const reps = useClubReps();
  const { existing } = props;
  if (existing && !reps.data) {
    return (
      <Dialog open={props.open} onClose={props.onClose} title="edit club">
        <p role={reps.isError ? 'alert' : 'status'} className="text-sm">
          {reps.isError ? "couldn't load reps — try again" : 'loading reps…'}
        </p>
        <div className="mt-2 flex justify-end">
          <Button variant="ghost" onClick={props.onClose} type="button">
            cancel
          </Button>
        </div>
      </Dialog>
    );
  }
  const initialReps = reps.data?.get(existing?.id ?? '') ?? [];
  return <ClubDialogBody key={existing?.id ?? 'new'} {...props} loadedReps={initialReps} />;
}

function ClubDialogBody({
  open,
  onClose,
  existing,
  loadedReps,
}: Props & { loadedReps: MemberSearchResult[] }) {
  const create = useCreateClub();
  const update = useUpdateClub(existing?.id ?? '');
  const [initialReps] = useState(loadedReps);
  const [reps, setReps] = useState<MemberSearchResult[]>(initialReps);
  const [createdId, setCreatedId] = useState<string | null>(null);
  const clubId = existing?.id ?? createdId ?? '';
  const setClubReps = useSetClubReps(clubId);
  const busy = create.isPending || update.isPending || setClubReps.isPending;
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
      let id = clubId;
      if (existing) await update.mutateAsync(input);
      else if (!createdId) {
        id = (await create.mutateAsync(input)).id;
        setCreatedId(id);
      }
      const ids = reps.map((r) => r.id);
      const before = new Set(initialReps.map((r) => r.id));
      if (ids.length !== before.size || ids.some((rid) => !before.has(rid))) {
        await setClubReps.mutateAsync({ userIds: ids, forClubId: id });
      }
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
        <MemberPicker
          label="reps"
          hint="they get reminder emails and can post this club's events"
          selected={reps}
          onChange={setReps}
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
