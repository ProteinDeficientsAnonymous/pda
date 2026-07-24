import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { CommentReactionSummary, CommentReactor } from '@/models/eventComment';
import { ReactionEmoji } from '@/models/eventComment';

import { ReactionBar } from './ReactionBar';

const summary = (
  emoji: string,
  count: number,
  mine = false,
  reactors: CommentReactor[] = [],
): CommentReactionSummary => ({
  emoji: emoji as CommentReactionSummary['emoji'],
  count,
  reactedByMe: mine,
  reactors,
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
    const heart = screen.getByRole('button', { name: /react with ❤️/u });
    expect(heart).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /who reacted with ❤️/u })).toHaveTextContent('3');
    // Other emojis are not in the bar; they're only in the picker (closed).
    expect(screen.queryByRole('button', { name: /react with 🔥/u })).not.toBeInTheDocument();
  });

  it('opens the voter popover on count click without toggling the reaction', () => {
    const onToggle = vi.fn();
    const reactor = { userId: 'u1', name: 'ash', photoUrl: '' };
    render(
      <ReactionBar
        reactions={[summary(ReactionEmoji.Heart, 1, true, [reactor])]}
        canReact
        onToggle={onToggle}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /who reacted with ❤️/u }));
    expect(onToggle).not.toHaveBeenCalled();
    expect(screen.getByRole('dialog', { name: /who reacted with ❤️/u })).toBeInTheDocument();
    expect(screen.getByText('ash')).toBeInTheDocument();
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
    fireEvent.click(screen.getByRole('button', { name: /react with ❤️/u }));
    expect(onToggle).toHaveBeenCalledWith(ReactionEmoji.Heart);
  });
});
