// Respond to a poll — yes / maybe / no per option. Each click POSTs the full
// merged votes map (idempotent). Dialog stays open so a member can change
// multiple options in one sitting; it closes only via backdrop / Escape /
// close button.

import { format } from 'date-fns';
import { toast } from 'sonner';
import { extractPollError, useVotePoll } from '@/api/eventPolls';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { cn } from '@/utils/cn';
import { ALL_VOTE_CHOICES, VoteChoice, type EventPoll } from '@/models/eventPoll';
import { sortOptionsChrono } from './pollHelpers';

interface Props {
  open: boolean;
  onClose: () => void;
  poll: EventPoll;
}

export function PollRespondDialog({ open, onClose, poll }: Props) {
  const vote = useVotePoll(poll.eventId);

  async function onPick(optionId: string, choice: VoteChoice) {
    const merged: Record<string, VoteChoice> = { ...poll.myVotes, [optionId]: choice };
    try {
      await vote.mutateAsync(merged);
    } catch (err) {
      toast.error(extractPollError(err));
    }
  }

  const options = sortOptionsChrono(poll.options);

  return (
    <Dialog open={open} onClose={onClose} title="respond to poll">
      <div className="flex flex-col gap-3">
        <p className="text-foreground-secondary text-sm">
          pick one per option — tap again to switch
        </p>

        <ul className="flex max-h-96 flex-col gap-2 overflow-y-auto">
          {options.map((opt) => {
            const myChoice = poll.myVotes[opt.id];
            return (
              <li
                key={opt.id}
                className="border-border bg-surface flex flex-col gap-2 rounded-md border p-3"
              >
                <span className="text-sm font-medium">
                  {format(opt.datetime, 'EEE MMM d · h:mm a').toLowerCase()}
                </span>
                <div className="flex gap-2">
                  {ALL_VOTE_CHOICES.map((c) => (
                    <ChoiceButton
                      key={c}
                      choice={c}
                      active={myChoice === c}
                      disabled={vote.isPending}
                      onClick={() => {
                        void onPick(opt.id, c);
                      }}
                    />
                  ))}
                </div>
              </li>
            );
          })}
        </ul>

        <div className="flex justify-end pt-2">
          <Button onClick={onClose}>done</Button>
        </div>
      </div>
    </Dialog>
  );
}

function ChoiceButton({
  choice,
  active,
  disabled,
  onClick,
}: {
  choice: VoteChoice;
  active: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  // Active styles differ per choice so a color-blind reader can still tell
  // "I voted yes" from "I voted no" via the leading check glyph + the label.
  const tone =
    choice === VoteChoice.Yes
      ? 'border-brand-600 bg-brand-50 text-brand-900'
      : choice === VoteChoice.Maybe
        ? 'border-warning bg-warning-subtle text-warning'
        : 'border-border-strong bg-surface-dim text-foreground-secondary';
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      className={cn(
        'flex-1 rounded-md border px-3 py-2 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50',
        active ? tone : 'border-border bg-surface text-foreground-secondary hover:bg-surface-dim',
      )}
    >
      {active ? '✓ ' : ''}
      {choice}
    </button>
  );
}
