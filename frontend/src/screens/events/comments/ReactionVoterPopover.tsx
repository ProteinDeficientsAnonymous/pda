import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';

import { useAuthStore } from '@/auth/store';
import type { CommentReactionSummary, CommentReactor } from '@/models/eventComment';

interface Props {
  reaction: CommentReactionSummary;
  onClose: () => void;
}

export function ReactionVoterPopover({ reaction, onClose }: Props) {
  const ref = useRef<HTMLDivElement | null>(null);
  const authed = useAuthStore((s) => s.status === 'authed');

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    function onDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener('keydown', onKey);
    // deferred: a long-press opens this while the pointer is still down, and
    // binding synchronously would let that same gesture close it immediately
    const bind = setTimeout(() => {
      document.addEventListener('mousedown', onDown);
    });
    return () => {
      clearTimeout(bind);
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
        {reaction.reactors.map((r) =>
          authed ? (
            <Link
              key={r.userId}
              to={`/members/${r.userId}`}
              onClick={onClose}
              className="hover:bg-surface-dim -mx-1 flex min-h-11 items-center gap-2 rounded px-1 text-sm"
            >
              <ReactorAvatar reactor={r} />
              {r.name}
            </Link>
          ) : (
            <span key={r.userId} className="flex items-center gap-2 py-1 text-sm">
              <ReactorAvatar reactor={r} />
              {r.name}
            </span>
          ),
        )}
      </div>
    </div>
  );
}

function ReactorAvatar({ reactor }: { reactor: CommentReactor }) {
  if (reactor.photoUrl) {
    return (
      <img
        src={reactor.photoUrl}
        alt=""
        className="h-5 w-5 shrink-0 rounded-full object-cover"
        loading="lazy"
      />
    );
  }
  return (
    <span
      aria-hidden="true"
      className="bg-toggle-off text-foreground-secondary flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs"
    >
      {reactor.name.slice(0, 1).toLowerCase()}
    </span>
  );
}
