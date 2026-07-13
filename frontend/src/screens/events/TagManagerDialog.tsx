import { type SyntheticEvent, useState } from 'react';

import { useCreateEventTag, useDeleteEventTag, useEventTags } from '@/api/eventTags';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { TextField } from '@/components/ui/TextField';
import { extractApiError } from '@/utils/errors';

interface Props {
  open: boolean;
  onClose: () => void;
}

export function TagManagerDialog({ open, onClose }: Props) {
  const { data: tags = [], isPending, isError } = useEventTags();
  const createTag = useCreateEventTag();
  const deleteTag = useDeleteEventTag();

  const [name, setName] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const trimmed = name.trim();

  async function run(action: Promise<unknown>, fallback: string) {
    setFormError(null);
    try {
      await action;
    } catch (err) {
      setFormError(extractApiError(err, fallback));
    }
  }

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    if (!trimmed) return;
    const created = createTag.mutateAsync(trimmed).then(() => {
      setName('');
    });
    await run(created, 'something went wrong — try again');
  }

  async function onConfirmDelete(id: string) {
    setConfirmingId(null);
    setDeletingId(id);
    await run(deleteTag.mutateAsync(id), "couldn't delete tag — try again");
    setDeletingId(null);
  }

  return (
    <Dialog open={open} onClose={onClose} title="manage tags">
      <div className="flex flex-col gap-4">
        {isPending ? <p className="text-muted text-sm">loading tags…</p> : null}
        {isError ? (
          <p className="text-destructive text-sm">couldn't load tags — try again</p>
        ) : null}
        {!isPending && !isError && tags.length === 0 ? (
          <p className="text-muted text-sm">no tags yet 🌿</p>
        ) : null}
        {tags.length > 0 ? (
          <ul className="flex flex-col gap-2" aria-label="existing tags">
            {tags.map((t) => (
              <li
                key={t.id}
                className="border-border bg-surface-dim flex flex-col gap-2 rounded-md border px-3 py-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-foreground truncate text-sm">{t.name}</span>
                  {confirmingId === t.id ? null : (
                    <Button
                      variant="ghost"
                      onClick={() => {
                        setConfirmingId(t.id);
                      }}
                      disabled={deletingId === t.id}
                    >
                      {deletingId === t.id ? 'deleting…' : 'delete'}
                    </Button>
                  )}
                </div>
                {confirmingId === t.id ? (
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-muted text-xs">
                      delete this tag? it will be removed from any events using it
                    </span>
                    <div className="flex shrink-0 items-center gap-1">
                      <Button
                        variant="ghost"
                        onClick={() => {
                          setConfirmingId(null);
                        }}
                      >
                        cancel
                      </Button>
                      <Button
                        variant="primary"
                        onClick={() => {
                          void onConfirmDelete(t.id);
                        }}
                      >
                        delete
                      </Button>
                    </div>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}

        <form
          onSubmit={(e) => {
            void onSubmit(e);
          }}
          className="flex items-end gap-2"
        >
          <div className="flex-1">
            <TextField
              label="new tag"
              value={name}
              maxLength={50}
              placeholder="e.g. walk"
              onChange={(e) => {
                setName(e.target.value);
                setFormError(null);
              }}
            />
          </div>
          <Button type="submit" disabled={createTag.isPending || !trimmed}>
            {createTag.isPending ? 'adding…' : 'add'}
          </Button>
        </form>

        {formError ? (
          <p role="alert" className="text-destructive text-sm break-words">
            {formError}
          </p>
        ) : null}

        <div className="flex justify-end">
          <Button type="button" variant="secondary" onClick={onClose}>
            done
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
