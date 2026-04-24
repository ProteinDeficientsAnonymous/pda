// Host-only option manager. Edit datetimes, add new options, remove
// existing ones, and nuke the whole poll. Each row is independent — the
// mutation fires on a per-row "save" so the host can leave mid-edit
// without losing other changes.

import { useState } from 'react';
import { format } from 'date-fns';
import { toast } from 'sonner';
import {
  extractPollError,
  useAddPollOption,
  useDeletePoll,
  useDeletePollOption,
  useUpdatePollOption,
} from '@/api/eventPolls';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { DateTimePicker } from '@/components/ui/DateTimePicker';
import type { EventPoll, EventPollOption } from '@/models/eventPoll';
import { sortOptionsChrono } from './pollHelpers';

interface Props {
  open: boolean;
  onClose: () => void;
  poll: EventPoll;
}

export function PollManageDialog({ open, onClose, poll }: Props) {
  const addOpt = useAddPollOption(poll.eventId);
  const updateOpt = useUpdatePollOption(poll.eventId);
  const deleteOpt = useDeletePollOption(poll.eventId);
  const deletePoll = useDeletePoll(poll.eventId);

  const [newIso, setNewIso] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  async function onAdd() {
    if (!newIso) return;
    if (new Date(newIso).getTime() < Date.now() - 60_000) {
      toast.error('options must be in the future');
      return;
    }
    try {
      await addOpt.mutateAsync(new Date(newIso));
      setNewIso(null);
      toast.success('option added');
    } catch (err) {
      toast.error(extractPollError(err));
    }
  }

  async function onDeletePoll() {
    try {
      await deletePoll.mutateAsync();
      toast.success('poll removed');
      setConfirmDelete(false);
      onClose();
    } catch (err) {
      toast.error(extractPollError(err));
    }
  }

  const options = sortOptionsChrono(poll.options);
  const busy =
    addOpt.isPending || updateOpt.isPending || deleteOpt.isPending || deletePoll.isPending;

  return (
    <Dialog open={open} onClose={onClose} title="edit poll options">
      <div className="flex flex-col gap-4">
        <ul className="flex flex-col gap-2">
          {options.map((opt) => (
            <OptionRow
              key={opt.id}
              option={opt}
              onUpdate={(iso) =>
                updateOpt.mutateAsync({ optionId: opt.id, datetime: new Date(iso) })
              }
              onDelete={() => deleteOpt.mutateAsync(opt.id)}
              disabled={busy}
            />
          ))}
        </ul>

        <div className="border-border flex flex-col gap-2 border-t pt-3">
          <span className="text-sm font-medium">add an option</span>
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <DateTimePicker label="date & time" value={newIso} onChange={setNewIso} disablePast />
            </div>
            <Button
              variant="secondary"
              onClick={() => {
                void onAdd();
              }}
              disabled={busy || !newIso}
            >
              add
            </Button>
          </div>
        </div>

        <div className="border-border flex flex-col gap-2 border-t pt-3">
          {confirmDelete ? (
            <>
              <p className="text-sm text-red-700">delete the whole poll? this can't be undone.</p>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  onClick={() => {
                    setConfirmDelete(false);
                  }}
                  disabled={busy}
                >
                  cancel
                </Button>
                <Button
                  onClick={() => {
                    void onDeletePoll();
                  }}
                  disabled={busy}
                  className="bg-red-600 hover:bg-red-700"
                >
                  {deletePoll.isPending ? 'deleting…' : 'yes, delete'}
                </Button>
              </div>
            </>
          ) : (
            <Button
              variant="ghost"
              onClick={() => {
                setConfirmDelete(true);
              }}
              disabled={busy}
              className="self-start text-red-700"
            >
              delete poll
            </Button>
          )}
        </div>

        <div className="flex justify-end pt-2">
          <Button onClick={onClose} disabled={busy}>
            done
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

function OptionRow({
  option,
  onUpdate,
  onDelete,
  disabled,
}: {
  option: EventPollOption;
  onUpdate: (iso: string) => Promise<unknown>;
  onDelete: () => Promise<unknown>;
  disabled: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [iso, setIso] = useState<string | null>(option.datetime.toISOString());
  const [saving, setSaving] = useState(false);

  async function save() {
    if (!iso) return;
    if (new Date(iso).getTime() < Date.now() - 60_000) {
      toast.error('options must be in the future');
      return;
    }
    setSaving(true);
    try {
      await onUpdate(iso);
      setEditing(false);
      toast.success('updated');
    } catch (err) {
      toast.error(extractPollError(err));
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    try {
      await onDelete();
      toast.success('removed');
    } catch (err) {
      toast.error(extractPollError(err));
    }
  }

  if (!editing) {
    return (
      <li className="border-border bg-surface flex items-center justify-between gap-2 rounded-md border p-2">
        <span className="text-sm">
          {format(option.datetime, 'EEE MMM d · h:mm a').toLowerCase()}
        </span>
        <div className="flex gap-1">
          <Button
            variant="ghost"
            onClick={() => {
              setEditing(true);
            }}
            disabled={disabled}
          >
            edit
          </Button>
          <Button
            variant="ghost"
            onClick={() => {
              void remove();
            }}
            disabled={disabled}
            className="text-red-700"
          >
            remove
          </Button>
        </div>
      </li>
    );
  }

  return (
    <li className="border-border bg-surface flex items-end gap-2 rounded-md border p-2">
      <div className="flex-1">
        <DateTimePicker label="date & time" value={iso} onChange={setIso} disablePast />
      </div>
      <Button
        variant="ghost"
        onClick={() => {
          setEditing(false);
          setIso(option.datetime.toISOString());
        }}
        disabled={saving}
      >
        cancel
      </Button>
      <Button
        onClick={() => {
          void save();
        }}
        disabled={saving || !iso}
      >
        {saving ? 'saving…' : 'save'}
      </Button>
    </li>
  );
}
