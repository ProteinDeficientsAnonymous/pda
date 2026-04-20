// Click-to-open popover showing who voted yes / maybe / no on a single option.
// Anchored to the card it's attached to — parent is relative, we're absolute.
// Dismisses on outside-click + Escape.

import { useEffect, useRef } from 'react';
import type { EventPollOption, PollVoter } from '@/models/eventPoll';

interface Props {
  option: EventPollOption;
  onClose: () => void;
}

export function PollVoterPopover({ option, onClose }: Props) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    function onDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onDown);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onDown);
    };
  }, [onClose]);

  const hasAnyVoter =
    option.yesVoters.length > 0 || option.maybeVoters.length > 0 || option.noVoters.length > 0;

  return (
    <div
      ref={ref}
      role="dialog"
      aria-label="voters"
      className="border-border bg-surface absolute top-full right-0 left-0 z-20 mt-2 rounded-md border p-3 shadow-(--shadow-lg)"
    >
      {hasAnyVoter ? (
        <div className="flex flex-col gap-3">
          <VoterRow label="yes" voters={option.yesVoters} />
          <VoterRow label="maybe" voters={option.maybeVoters} />
          <VoterRow label="no" voters={option.noVoters} />
        </div>
      ) : (
        <p className="text-foreground-tertiary text-sm">no one's voted on this one yet 🌿</p>
      )}
    </div>
  );
}

function VoterRow({ label, voters }: { label: string; voters: readonly PollVoter[] }) {
  if (voters.length === 0) return null;
  return (
    <div>
      <h3 className="text-foreground-tertiary mb-1 text-xs font-medium tracking-wide">
        {label} · {voters.length}
      </h3>
      <div className="flex flex-wrap gap-2">
        {voters.map((v) => (
          <VoterChip key={v.userId} voter={v} />
        ))}
      </div>
    </div>
  );
}

function VoterChip({ voter }: { voter: PollVoter }) {
  return (
    <span className="bg-surface-dim inline-flex items-center gap-2 rounded-full px-2 py-1 text-sm">
      {voter.photoUrl ? (
        <img
          src={voter.photoUrl}
          alt=""
          className="h-6 w-6 rounded-full object-cover"
          loading="lazy"
        />
      ) : (
        <span
          aria-hidden="true"
          className="bg-toggle-off text-foreground-secondary flex h-6 w-6 items-center justify-center rounded-full text-xs"
        >
          {voter.name.slice(0, 1).toLowerCase()}
        </span>
      )}
      {voter.name}
    </span>
  );
}
