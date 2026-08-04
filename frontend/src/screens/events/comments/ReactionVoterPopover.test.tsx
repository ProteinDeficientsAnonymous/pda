import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import type { CommentReactionSummary } from '@/models/eventComment';
import { ReactionEmoji } from '@/models/eventComment';

import { ReactionVoterPopover } from './ReactionVoterPopover';

const { authStatus } = vi.hoisted(() => ({ authStatus: { value: 'authed' } }));

vi.mock('@/auth/store', () => ({
  useAuthStore: (selector: (s: { status: string }) => unknown) =>
    selector({ status: authStatus.value }),
}));

const reaction: CommentReactionSummary = {
  emoji: ReactionEmoji.Heart,
  count: 2,
  reactedByMe: false,
  reactors: [
    { userId: 'u1', name: 'ash', photoUrl: '' },
    { userId: 'u2', name: 'robin', photoUrl: 'https://example.test/robin.jpg' },
  ],
};

const wrap = (ui: ReactNode) => render(<MemoryRouter>{ui}</MemoryRouter>);

describe('ReactionVoterPopover', () => {
  it('links each reactor to their profile when authed', () => {
    authStatus.value = 'authed';
    wrap(<ReactionVoterPopover reaction={reaction} onClose={vi.fn()} />);

    expect(screen.getByRole('link', { name: /ash/ })).toHaveAttribute('href', '/members/u1');
    expect(screen.getByRole('link', { name: /robin/ })).toHaveAttribute('href', '/members/u2');
  });

  it('closes the popover when a reactor is followed', async () => {
    authStatus.value = 'authed';
    const onClose = vi.fn();
    const { default: userEvent } = await import('@testing-library/user-event');
    wrap(<ReactionVoterPopover reaction={reaction} onClose={onClose} />);

    await userEvent.click(screen.getByRole('link', { name: /ash/ }));
    expect(onClose).toHaveBeenCalled();
  });

  it('renders names without links when signed out', () => {
    authStatus.value = 'unauthed';
    wrap(<ReactionVoterPopover reaction={reaction} onClose={vi.fn()} />);

    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getByText('ash')).toBeInTheDocument();
    expect(screen.getByText('robin')).toBeInTheDocument();
  });
});
