// Dual-mode poll creator.
//
//   live mode   — eventId present. "create poll" fires useCreatePoll.
//   buffer mode — onBuffer provided (EventForm, pre-save). Options are
//                 returned to the parent, which queues them and fires the
//                 create-poll request after useCreateEvent settles.
//
// Reason: the event-create form doesn't have an event_id yet, and we don't
// want to force a round-trip save just to start a poll.

import { useState } from 'react';
import { toast } from 'sonner';
import { useCreatePoll, extractPollError } from '@/api/eventPolls';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { DateTimePicker } from '@/components/ui/DateTimePicker';

interface Props {
  open: boolean;
  onClose: () => void;
  // Exactly one of these must be provided.
  eventId?: string | undefined;
  onBuffer?: ((datetimes: Date[]) => void) | undefined;
  initialOptions?: readonly string[] | undefined; // ISO strings — used by buffer mode to reopen with existing queue
}

const MIN_OPTIONS = 2;
const MAX_OPTIONS = 10;

// Wrapper gates mount on `open` so the body's useState initializer re-runs
// every time the dialog opens. Without this, clicking "edit" on a queued
// batch would show two empty rows (the stale mount-time init).
export function PollCreateDialog(props: Props) {
  if (!props.open) return null;
  return <PollCreateDialogBody {...props} />;
}

function PollCreateDialogBody({ onClose, eventId, onBuffer, initialOptions }: Props) {
  const createPoll = useCreatePoll(eventId ?? '');
  const [rows, setRows] = useState<(string | null)[]>(() =>
    initialOptions && initialOptions.length > 0 ? [...initialOptions] : [null, null],
  );
  const [error, setError] = useState<string | null>(null);

  function close() {
    setError(null);
    onClose();
  }

  function addRow() {
    if (rows.length >= MAX_OPTIONS) return;
    setRows((r) => [...r, null]);
  }

  function removeRow(idx: number) {
    setRows((r) => (r.length <= 1 ? r : r.filter((_, i) => i !== idx)));
  }

  function updateRow(idx: number, iso: string | null) {
    setRows((r) => r.map((v, i) => (i === idx ? iso : v)));
  }

  async function submit() {
    const chosen = rows.filter((v): v is string => !!v);
    const unique = Array.from(new Set(chosen));
    if (unique.length < MIN_OPTIONS) {
      setError(`pick at least ${String(MIN_OPTIONS)} distinct dates`);
      return;
    }
    if (unique.length !== chosen.length) {
      setError('some options are duplicates — remove them or pick different times');
      return;
    }
    const cutoff = Date.now() - 60_000;
    if (unique.some((iso) => new Date(iso).getTime() < cutoff)) {
      setError('options must be in the future');
      return;
    }
    setError(null);

    const datetimes = unique.map((iso) => new Date(iso));

    if (onBuffer) {
      onBuffer(datetimes);
      toast.success('dates queued 🌱');
      close();
      return;
    }
    if (!eventId) {
      setError('missing event');
      return;
    }
    try {
      await createPoll.mutateAsync(datetimes);
      toast.success('poll created 🌱');
      close();
    } catch (err) {
      setError(extractPollError(err));
    }
  }

  const submitting = createPoll.isPending;

  return (
    <Dialog open onClose={close} title="poll for dates">
      <div className="flex flex-col gap-3">
        <p className="text-foreground-secondary text-sm">
          add a few times — members vote yes / maybe / no on each
        </p>

        <ul className="flex flex-col gap-3">
          {rows.map((iso, idx) => (
            <li key={idx} className="flex items-end gap-2">
              <div className="flex-1">
                <DateTimePicker
                  label={`option ${String(idx + 1)}`}
                  value={iso}
                  onChange={(next) => {
                    updateRow(idx, next);
                  }}
                  optional={false}
                />
              </div>
              <button
                type="button"
                onClick={() => {
                  removeRow(idx);
                }}
                disabled={rows.length <= 1}
                aria-label={`remove option ${String(idx + 1)}`}
                className="border-border text-foreground-tertiary hover:bg-surface-dim h-10 rounded-md border px-3 text-sm disabled:cursor-not-allowed disabled:opacity-50"
              >
                ×
              </button>
            </li>
          ))}
        </ul>

        <Button
          variant="ghost"
          onClick={addRow}
          disabled={rows.length >= MAX_OPTIONS}
          className="self-start"
        >
          + add option
        </Button>

        {error ? (
          <p
            role="alert"
            className="rounded-md border border-red-200 bg-red-50 p-2 text-sm text-red-700"
          >
            {error}
          </p>
        ) : null}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={close} disabled={submitting}>
            cancel
          </Button>
          <Button
            onClick={() => {
              void submit();
            }}
            disabled={submitting}
          >
            {submitting ? 'creating…' : onBuffer ? 'queue dates' : 'create poll'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
