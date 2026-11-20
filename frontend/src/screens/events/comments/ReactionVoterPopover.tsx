import type { RefObject } from 'react';
import { useEffect } from 'react';
import { Link } from 'react-router-dom';

import { useAuthStore } from '@/auth/store';
import type { CommentReactionSummary, CommentReactor } from '@/models/eventComment';

interface Props {
  reaction: CommentReactionSummary;
  insideRef: RefObject<HTMLElement | null>;
  onClose: () => void;
}

export function ReactionVoterPopover({ reaction, insideRef, onClose }: Props) {
  const authed = useAuthStore((s) => s.status === 'authed');

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    // pointerdown, not mousedown: iOS replays a mouse press on the emoji after a long press lifts
    function onDown(e: PointerEvent) {
      if (!insideRef.current?.contains(e.target as Node)) onClose();
    }
    document.addEventListener('keydown', onKey);
    // deferred so the press that opened the popover can't also dismiss it
    const bind = setTimeout(() => {
      document.addEventListener('pointerdown', onDown);
    });
    return () => {
      clearTimeout(bind);
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onDown);
    };
  }, [insideRef, onClose]);

  return (
    <div
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
