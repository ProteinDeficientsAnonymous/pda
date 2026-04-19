// Horizontal strip of poll-option cards. Scrolls on small screens so long
// option lists don't wrap into a messy grid.

import type { EventPoll } from '@/models/eventPoll';
import { sortOptionsChrono } from './pollHelpers';
import { PollOptionCard } from './PollOptionCard';

interface Props {
  poll: EventPoll;
}

export function PollOptionStrip({ poll }: Props) {
  const sorted = sortOptionsChrono(poll.options);
  const isFinalized = !!poll.winningOptionId;

  return (
    <ul className="-mx-1 flex gap-2 overflow-x-auto px-1 py-1">
      {sorted.map((opt) => (
        <PollOptionCard
          key={opt.id}
          option={opt}
          isWinner={poll.winningOptionId === opt.id}
          isFinalized={isFinalized}
        />
      ))}
    </ul>
  );
}
