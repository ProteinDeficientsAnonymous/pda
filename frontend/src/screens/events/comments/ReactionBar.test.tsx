import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { CommentReactionSummary } from '@/models/eventComment';
import { ReactionEmoji } from '@/models/eventComment';

import { ReactionBar } from './ReactionBar';

const summary = (emoji: string, count: number, mine = false): CommentReactionSummary => ({
  emoji: emoji as CommentReactionSummary['emoji'],
  count,
  reactedByMe: mine,
});

describe('ReactionBar', () => {
  it('renders only existing reactions with their counts', () => {
    render(
      <ReactionBar
        reactions={[summary(ReactionEmoji.Heart, 3, true)]}
        canReact
        onToggle={vi.fn()}
      />,
    );
    const heart = screen.getByRole('button', { name: /❤️/u });
    expect(heart).toHaveAttribute('aria-pressed', 'true');
    expect(heart).toHaveTextContent('3');
    // Other emojis are not in the bar; they're only in the picker (closed).
    expect(screen.queryByRole('button', { name: /🔥/u })).not.toBeInTheDocument();
  });

  it('shows the add-reaction button when canReact', () => {
    render(<ReactionBar reactions={[]} canReact onToggle={vi.fn()} />);
    expect(screen.getByRole('button', { name: /add reaction/i })).toBeInTheDocument();
  });

  it('hides the add-reaction button when canReact is false', () => {
    render(<ReactionBar reactions={[]} canReact={false} onToggle={vi.fn()} />);
    expect(screen.queryByRole('button', { name: /add reaction/i })).not.toBeInTheDocument();
  });

  it('opens the picker on add-reaction click and toggles the chosen emoji', () => {
    const onToggle = vi.fn();
    render(<ReactionBar reactions={[]} canReact onToggle={onToggle} />);
    fireEvent.click(screen.getByRole('button', { name: /add reaction/i }));
    fireEvent.click(screen.getByRole('button', { name: /🌱/u }));
    expect(onToggle).toHaveBeenCalledWith(ReactionEmoji.Seedling);
  });

  it('clicking an existing reaction toggles it', () => {
    const onToggle = vi.fn();
    render(
      <ReactionBar
        reactions={[summary(ReactionEmoji.Heart, 1, true)]}
        canReact
        onToggle={onToggle}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /❤️/u }));
    expect(onToggle).toHaveBeenCalledWith(ReactionEmoji.Heart);
  });
});
