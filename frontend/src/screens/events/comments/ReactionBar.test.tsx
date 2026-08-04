import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { CommentReactionSummary, CommentReactor } from '@/models/eventComment';
import { ReactionEmoji } from '@/models/eventComment';

import { ReactionBar } from './ReactionBar';

// the voter popover links reactors only when authed; the bar's own behaviour
// is auth-independent, so pin it signed-out to keep these tests router-free
vi.mock('@/auth/store', () => ({
  useAuthStore: (selector: (s: { status: string }) => unknown) => selector({ status: 'unauthed' }),
}));

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
    render(<ReactionBar reactions={[summary(ReactionEmoji.Heart, 3, true)]} onToggle={vi.fn()} />);
    // the count rides in the label so screen readers announce it with the emoji
    const heart = screen.getByRole('button', { name: 'react with ❤️ 3' });
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
        onToggle={onToggle}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /who reacted with ❤️/u }));
    expect(onToggle).not.toHaveBeenCalled();
    expect(screen.getByRole('dialog', { name: /who reacted with ❤️/u })).toBeInTheDocument();
    expect(screen.getByText('ash')).toBeInTheDocument();
  });

  it('lists every reactor in the popover', () => {
    render(
      <ReactionBar
        reactions={[
          summary(ReactionEmoji.Heart, 2, true, [
            { userId: 'u1', name: 'ash', photoUrl: '' },
            { userId: 'u2', name: 'robin', photoUrl: '' },
          ]),
        ]}
        onToggle={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /who reacted with ❤️/u }));
    expect(screen.getByText('ash')).toBeInTheDocument();
    expect(screen.getByText('robin')).toBeInTheDocument();
  });

  it('opens the voters on long press without toggling the reaction', () => {
    vi.useFakeTimers();
    const onToggle = vi.fn();
    render(
      <ReactionBar
        reactions={[
          summary(ReactionEmoji.Heart, 1, true, [{ userId: 'u1', name: 'ash', photoUrl: '' }]),
        ]}
        onToggle={onToggle}
      />,
    );
    const emoji = screen.getByRole('button', { name: /react with ❤️/u });
    fireEvent.pointerDown(emoji, { clientX: 0, clientY: 0, button: 0 });
    // the popover mounts mid-hold, so the rest of the gesture lands on it
    act(() => {
      vi.advanceTimersByTime(500);
    });
    fireEvent.mouseDown(emoji, { clientX: 0, clientY: 0, button: 0 });
    fireEvent.pointerUp(emoji, { button: 0 });
    fireEvent.mouseUp(emoji, { button: 0 });
    fireEvent.click(emoji);
    act(() => {
      vi.advanceTimersByTime(50);
    });

    expect(onToggle).not.toHaveBeenCalled();
    expect(screen.getByRole('dialog', { name: /who reacted with ❤️/u })).toBeInTheDocument();
    vi.useRealTimers();
  });

  it('keeps the voters open when the press drifts off the button', () => {
    vi.useFakeTimers();
    render(
      <ReactionBar
        reactions={[
          summary(ReactionEmoji.Heart, 1, true, [{ userId: 'u1', name: 'ash', photoUrl: '' }]),
        ]}
        onToggle={vi.fn()}
      />,
    );
    const emoji = screen.getByRole('button', { name: /react with ❤️/u });
    fireEvent.pointerDown(emoji, { clientX: 0, clientY: 0, button: 0 });
    fireEvent.pointerMove(emoji, { clientX: 3, clientY: 3 });
    fireEvent.pointerLeave(emoji);
    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(screen.getByRole('dialog', { name: /who reacted with ❤️/u })).toBeInTheDocument();
    vi.useRealTimers();
  });

  it('cancels the long press when the pointer moves away', () => {
    vi.useFakeTimers();
    const onToggle = vi.fn();
    render(
      <ReactionBar
        reactions={[
          summary(ReactionEmoji.Heart, 1, true, [{ userId: 'u1', name: 'ash', photoUrl: '' }]),
        ]}
        onToggle={onToggle}
      />,
    );
    const emoji = screen.getByRole('button', { name: /react with ❤️/u });
    fireEvent.pointerDown(emoji, { clientX: 0, clientY: 0, button: 0 });
    fireEvent.pointerMove(emoji, { clientX: 60, clientY: 60 });
    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it('toggles normally on a short press', () => {
    vi.useFakeTimers();
    const onToggle = vi.fn();
    render(<ReactionBar reactions={[summary(ReactionEmoji.Heart, 1, true)]} onToggle={onToggle} />);
    const emoji = screen.getByRole('button', { name: /react with ❤️/u });
    fireEvent.pointerDown(emoji, { clientX: 0, clientY: 0, button: 0 });
    act(() => {
      vi.advanceTimersByTime(100);
    });
    fireEvent.pointerUp(emoji, { button: 0 });
    fireEvent.click(emoji);

    expect(onToggle).toHaveBeenCalledWith(ReactionEmoji.Heart);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it('shows the add-reaction button', () => {
    render(<ReactionBar reactions={[]} onToggle={vi.fn()} />);
    expect(screen.getByRole('button', { name: /add reaction/i })).toBeInTheDocument();
  });

  it('opens the picker on add-reaction click and toggles the chosen emoji', () => {
    const onToggle = vi.fn();
    render(<ReactionBar reactions={[]} onToggle={onToggle} />);
    fireEvent.click(screen.getByRole('button', { name: /add reaction/i }));
    fireEvent.click(screen.getByRole('button', { name: /🌱/u }));
    expect(onToggle).toHaveBeenCalledWith(ReactionEmoji.Seedling);
  });

  it('clicking an existing reaction toggles it', () => {
    const onToggle = vi.fn();
    render(<ReactionBar reactions={[summary(ReactionEmoji.Heart, 1, true)]} onToggle={onToggle} />);
    fireEvent.click(screen.getByRole('button', { name: /react with ❤️/u }));
    expect(onToggle).toHaveBeenCalledWith(ReactionEmoji.Heart);
  });

  // guards the e2e selectors: the picker option is the only button named
  // exactly '❤️', so an existing pill can't shadow it
  it('keeps the picker emoji distinct from the pill buttons', () => {
    render(<ReactionBar reactions={[summary(ReactionEmoji.Heart, 1, true)]} onToggle={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /add reaction/i }));

    expect(screen.getByRole('button', { name: '❤️' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'react with ❤️ 1' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'who reacted with ❤️' })).toBeInTheDocument();
  });
});
