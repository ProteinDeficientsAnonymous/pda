// Host-only finalize dialog. Radio list of options with the current leader
// pre-selected. Warns if event.endDatetime is set (backend finalize won't
// update end-time; host has to fix it after).

import { useState } from 'react';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { extractPollError, useFinalizePoll } from '@/api/eventPolls';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import type { Event } from '@/models/event';
import type { EventPoll } from '@/models/eventPoll';
import { pickFinalizeDefault, sortOptionsChrono } from './pollHelpers';

interface Props {
  open: boolean;
  onClose: () => void;
  event: Event;
  poll: EventPoll;
}

export function PollFinalizeDialog({ open, onClose, event, poll }: Props) {
  const finalize = useFinalizePoll(event.id);
  const [selected, setSelected] = useState<string | null>(
    () => pickFinalizeDefault(poll.options)?.id ?? null,
  );
  const [error, setError] = useState<string | null>(null);

  function close() {
    setSelected(pickFinalizeDefault(poll.options)?.id ?? null);
    setError(null);
    onClose();
  }

  async function submit() {
    if (!selected) {
      setError('pick a winner');
      return;
    }
    setError(null);
    try {
      await finalize.mutateAsync(selected);
      toast.success('poll finalized 🌱');
      close();
    } catch (err) {
      setError(extractPollError(err));
    }
  }

  const hasEndTime = !!event.endDatetime;
  const options = sortOptionsChrono(poll.options);
  const submitting = finalize.isPending;

  return (
    <Dialog open={open} onClose={close} title="finalize date">
      <div className="flex flex-col gap-3">
        <p className="text-foreground-secondary text-sm">
          pick the winning date — yes-voters get auto-rsvp'd
        </p>

        {hasEndTime ? (
          <p
            role="alert"
            className="rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900"
          >
            heads up — this won't update the end time. edit the event after to fix it.
          </p>
        ) : null}

        <ul className="flex max-h-80 flex-col gap-2 overflow-y-auto">
          {options.map((opt) => {
            const isSelected = selected === opt.id;
            return (
              <li key={opt.id}>
                <button
                  type="button"
                  onClick={() => {
                    setSelected(opt.id);
                  }}
                  aria-pressed={isSelected}
                  className={`flex w-full cursor-pointer items-center gap-3 rounded-md border p-3 text-left transition-colors ${
                    isSelected
                      ? 'border-brand-600 bg-brand-50'
                      : 'border-border bg-surface hover:bg-surface-dim'
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`flex h-4 w-4 flex-none items-center justify-center rounded-full border ${
                      isSelected
                        ? 'border-brand-600 bg-brand-600'
                        : 'border-border-strong bg-surface'
                    }`}
                  >
                    {isSelected ? <span className="h-1.5 w-1.5 rounded-full bg-white" /> : null}
                  </span>
                  <div className="flex flex-1 flex-col">
                    <span className="text-sm font-medium">
                      {format(opt.datetime, 'EEE MMM d · h:mm a').toLowerCase()}
                    </span>
                    <span className="text-foreground-tertiary text-xs">
                      {opt.yesCount} yes · {opt.maybeCount} maybe · {opt.noCount} no
                    </span>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>

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
            disabled={submitting || !selected}
          >
            {submitting ? 'finalizing…' : 'finalize date'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
