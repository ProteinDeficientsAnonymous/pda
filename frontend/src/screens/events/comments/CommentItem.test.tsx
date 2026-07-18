import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

const { mockPost } = vi.hoisted(() => ({ mockPost: vi.fn().mockResolvedValue({ data: {} }) }));

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: mockPost,
    delete: vi.fn(),
  },
}));

vi.mock('@/auth/store', () => ({
  useAuthStore: (selector: (s: { status: string }) => unknown) => selector({ status: 'authed' }),
}));

import type { EventComment } from '@/models/eventComment';

import { CommentItem } from './CommentItem';

function wrap(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const baseComment: EventComment = {
  id: 'c1',
  authorId: 'u1',
  authorDisplayName: 'Alice',
  authorPhotoUrl: '',
  body: 'hello',
  isDeleted: false,
  createdAt: '2026-01-01T00:00:00Z',
  reactions: [],
  canDelete: false,
  replies: [],
};

describe('CommentItem', () => {
  it('renders the body and author', () => {
    wrap(<CommentItem comment={baseComment} eventId="evt" canReact canReply />);
    expect(screen.getByText('hello')).toBeInTheDocument();
    expect(screen.getByText('alice')).toBeInTheDocument();
  });

  it('renders [deleted] placeholder when isDeleted', () => {
    wrap(
      <CommentItem
        comment={{ ...baseComment, isDeleted: true, body: '' }}
        eventId="evt"
        canReact
        canReply
      />,
    );
    expect(screen.getByText('[deleted]')).toBeInTheDocument();
    expect(screen.queryByRole('group', { name: 'reactions' })).not.toBeInTheDocument();
  });

  it('shows delete only when canDelete is true', () => {
    wrap(
      <CommentItem
        comment={{ ...baseComment, canDelete: false }}
        eventId="evt"
        canReact
        canReply
      />,
    );
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
  });

  it('includes the rsvp token when a non-member posts a reply', async () => {
    mockPost.mockClear();
    const user = userEvent.setup();
    wrap(<CommentItem comment={baseComment} eventId="evt" token="rsvp-token" canReact canReply />);
    await user.click(screen.getByRole('button', { name: 'reply' }));
    await user.type(screen.getByPlaceholderText('reply…'), 'hi there');
    await user.click(screen.getByRole('button', { name: 'post' }));

    expect(mockPost).toHaveBeenCalledWith(
      '/api/community/events/evt/comments/c1/replies/',
      { body: 'hi there' },
      { params: { token: 'rsvp-token' } },
    );
  });
});
