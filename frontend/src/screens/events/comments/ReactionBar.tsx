import { useEffect, useRef, useState } from 'react';

import type { CommentReactionSummary, ReactionEmojiValue } from '@/models/eventComment';
import { REACTION_EMOJI_ORDER } from '@/models/eventComment';

import { ReactionVoterPopover } from './ReactionVoterPopover';

interface Props {
  reactions: CommentReactionSummary[];
  canReact: boolean;
  onToggle: (emoji: ReactionEmojiValue) => void;
  disabledReason?: string | undefined;
}

export function ReactionBar({ reactions, canReact, onToggle, disabledReason }: Props) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [openVotersEmoji, setOpenVotersEmoji] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!pickerOpen) return;
    const handler = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) {
        setPickerOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => {
      document.removeEventListener('mousedown', handler);
    };
  }, [pickerOpen]);

  const handlePick = (emoji: ReactionEmojiValue) => {
    onToggle(emoji);
    setPickerOpen(false);
  };

  return (
    <div
      className="relative flex flex-wrap items-center gap-1"
      role="group"
      aria-label="reactions"
      ref={containerRef}
    >
      {reactions.map((r) => (
        <div
          key={r.emoji}
          className={[
            'relative inline-flex items-center gap-1 rounded-full border pl-2 text-sm transition',
            r.reactedByMe
              ? 'bg-brand-50 border-brand-500 text-foreground'
              : 'border-border-strong bg-surface text-foreground hover:bg-surface-dim',
          ].join(' ')}
        >
          <button
            type="button"
            aria-pressed={r.reactedByMe}
            aria-label={`react with ${r.emoji}`}
            disabled={!canReact}
            title={!canReact ? disabledReason : undefined}
            onClick={() => {
              onToggle(r.emoji);
            }}
            className={['py-0.5', !canReact ? 'cursor-not-allowed opacity-50' : ''].join(' ')}
          >
            {r.emoji}
          </button>
          <button
            type="button"
            aria-label={`who reacted with ${r.emoji}`}
            aria-expanded={openVotersEmoji === r.emoji}
            className="py-0.5 pr-2 text-xs underline decoration-dotted underline-offset-2"
            onClick={() => {
              setOpenVotersEmoji((cur) => (cur === r.emoji ? null : r.emoji));
            }}
          >
            {r.count}
          </button>
          {openVotersEmoji === r.emoji ? (
            <ReactionVoterPopover
              reaction={r}
              onClose={() => {
                setOpenVotersEmoji(null);
              }}
            />
          ) : null}
        </div>
      ))}
      {canReact ? (
        <button
          type="button"
          aria-label="add reaction"
          aria-expanded={pickerOpen}
          onClick={() => {
            setPickerOpen((v) => !v);
          }}
          className="border-border-strong bg-surface text-foreground-tertiary hover:bg-surface-dim inline-flex items-center gap-0.5 rounded-full border px-2 py-0.5 text-sm transition"
        >
          <span aria-hidden="true" className="text-xs leading-none">
            +
          </span>
          <AddReactionIcon />
        </button>
      ) : null}
      {pickerOpen ? (
        <div className="border-border-strong bg-surface absolute top-full left-0 z-10 mt-1 flex gap-1 rounded-md border p-1 shadow-md">
          {REACTION_EMOJI_ORDER.map((emoji) => (
            <button
              key={emoji}
              type="button"
              onClick={() => {
                handlePick(emoji);
              }}
              className="hover:bg-surface-dim inline-flex items-center rounded px-1.5 py-0.5 text-base transition"
            >
              {emoji}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function AddReactionIcon() {
  return (
    <svg
      aria-hidden="true"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M8 14s1.5 2 4 2 4-2 4-2" />
      <line x1="9" y1="9" x2="9.01" y2="9" />
      <line x1="15" y1="9" x2="15.01" y2="9" />
    </svg>
  );
}
