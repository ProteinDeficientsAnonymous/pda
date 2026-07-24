import { useEffect, useRef } from 'react';

import type { CommentReactionSummary } from '@/models/eventComment';

interface Props {
  reaction: CommentReactionSummary;
  onClose: () => void;
}

export function ReactionVoterPopover({ reaction, onClose }: Props) {
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

  return (
    <div
      ref={ref}
      role="dialog"
      aria-label={`who reacted with ${reaction.emoji}`}
      className="border-border bg-surface absolute top-full left-0 z-20 mt-1 min-w-40 rounded-md border p-2 shadow-(--shadow-lg)"
    >
      <div className="flex flex-col gap-1">
        {reaction.reactors.map((r) => (
          <span key={r.userId} className="flex items-center gap-2 text-sm">
            {r.photoUrl ? (
              <img
                src={r.photoUrl}
                alt=""
                className="h-5 w-5 rounded-full object-cover"
                loading="lazy"
              />
            ) : (
              <span
                aria-hidden="true"
                className="bg-toggle-off text-foreground-secondary flex h-5 w-5 items-center justify-center rounded-full text-xs"
              >
                {r.name.slice(0, 1).toLowerCase()}
              </span>
            )}
            {r.name}
          </span>
        ))}
      </div>
    </div>
  );
}
