import { format } from 'date-fns';
import { useState } from 'react';

import type { EventPollOption } from '@/models/eventPoll';
import { cn } from '@/utils/cn';

import { PollVoterPopover } from './PollVoterPopover';

interface Props {
  option: EventPollOption;
  isWinner: boolean;
  isFinalized: boolean;
}

export function PollOptionCard({ option, isWinner, isFinalized }: Props) {
  const [open, setOpen] = useState(false);

  const dayOfWeek = format(option.datetime, 'EEE').toLowerCase();
  const monthDay = format(option.datetime, 'MMM d').toLowerCase();
  const time = format(option.datetime, 'h:mm a').toLowerCase();

  const fade = isFinalized && !isWinner;

  return (
    <li className="relative">
      <button
        type="button"
        onClick={() => {
          setOpen((o) => !o);
        }}
        aria-expanded={open}
        aria-label={`${dayOfWeek} ${monthDay} ${time} — ${String(option.yesCount)} yes, ${String(option.maybeCount)} maybe, ${String(option.noCount)} no`}
        className={cn(
          'flex w-32 flex-col items-start gap-1 rounded-md border p-3 text-left transition-colors',
          isWinner
            ? 'border-brand-600 bg-brand-50 shadow-(--shadow-sm)'
            : 'border-border bg-surface hover:bg-surface-dim',
          fade && 'opacity-60',
        )}
      >
        <span className="text-foreground-tertiary text-xs font-medium tracking-wide">
          {dayOfWeek}
          {isWinner ? <span className="text-brand-700 ml-1">✓</span> : null}
        </span>
        <span className="text-base font-medium">{monthDay}</span>
        <span className="text-foreground-secondary text-sm">{time}</span>
        <span className="text-foreground-tertiary mt-1 text-xs">
          {option.yesCount} yes · {option.maybeCount} maybe
        </span>
      </button>
      {open ? (
        <PollVoterPopover
          option={option}
          onClose={() => {
            setOpen(false);
          }}
        />
      ) : null}
    </li>
  );
}
