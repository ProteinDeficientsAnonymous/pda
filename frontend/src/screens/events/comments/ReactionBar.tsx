import type { CommentReactionSummary, ReactionEmojiValue } from '@/models/eventComment';
import { REACTION_EMOJI_ORDER } from '@/models/eventComment';

interface Props {
  reactions: CommentReactionSummary[];
  canReact: boolean;
  onToggle: (emoji: ReactionEmojiValue) => void;
  disabledReason?: string | undefined;
}

export function ReactionBar({ reactions, canReact, onToggle, disabledReason }: Props) {
  const byEmoji = new Map(reactions.map((r) => [r.emoji, r]));
  return (
    <div className="flex flex-wrap gap-1" role="group" aria-label="reactions">
      {REACTION_EMOJI_ORDER.map((emoji) => {
        const summary = byEmoji.get(emoji);
        const count = summary?.count ?? 0;
        const pressed = summary?.reactedByMe ?? false;
        return (
          <button
            key={emoji}
            type="button"
            aria-pressed={pressed}
            disabled={!canReact}
            title={!canReact ? disabledReason : undefined}
            onClick={() => { onToggle(emoji); }}
            className={[
              'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-sm transition',
              pressed
                ? 'bg-brand-50 border-brand-500 text-foreground'
                : 'border-border-strong bg-surface text-foreground hover:bg-surface-dim',
              !canReact ? 'opacity-50 cursor-not-allowed' : '',
            ].join(' ')}
          >
            <span>{emoji}</span>
            {count > 0 ? <span className="text-xs">{count}</span> : null}
          </button>
        );
      })}
    </div>
  );
}
