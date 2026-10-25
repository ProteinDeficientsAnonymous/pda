import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { useEventSource } from '@/hooks/useEventSource';

import { EventCommentsCard } from './EventCommentsCard';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('@/hooks/useEventSource', () => ({ useEventSource: vi.fn() }));

const authState = vi.hoisted(() => ({ status: 'authed' }));

vi.mock('@/auth/store', () => {
  const state = {
    get status() {
      return authState.status;
    },
    user: { id: 'u-me', profilePhotoUrl: null },
  };
  const useAuthStore = vi.fn((selector?: (s: typeof state) => unknown) =>
    selector ? selector(state) : state,
  ) as unknown as {
    (selector: (s: typeof state) => unknown): unknown;
    getState: () => typeof state;
  };
  useAuthStore.getState = () => state;
  return { useAuthStore };
});

// Import after mocks

const eventId = '11111111-1111-1111-1111-111111111111';

function renderCard(token?: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <EventCommentsCard eventId={eventId} token={token} />
    </QueryClientProvider>,
  );
}

function lastStreamOptions() {
  return vi.mocked(useEventSource).mock.lastCall![0];
}

beforeEach(() => {
  vi.clearAllMocks();
  authState.status = 'authed';
});
afterEach(() => {
  vi.restoreAllMocks();
});

describe('EventCommentsCard', () => {
  it('shows the composer when the viewer can post', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], can_post: true, cannot_post_reason: null },
    });
    renderCard();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /post/i })).toBeInTheDocument();
    });
  });

  it('shows the rsvp prompt when the viewer is logged in but not RSVPd', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { items: [], can_post: false, cannot_post_reason: 'rsvp_required' },
    });
    renderCard();
    await waitFor(() => {
      expect(screen.getByText(/rsvp to join the conversation/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: /post/i })).not.toBeInTheDocument();
  });

  it('hides the comment thread when the viewer has no active rsvp', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        items: [
          {
            id: 'c1',
            author_id: 'other',
            author_display_name: 'someone',
            author_photo_url: '',
            body: 'leaked comment',
            is_deleted: false,
            created_at: new Date().toISOString(),
            reactions: [],
            can_delete: false,
            replies: [],
          },
        ],
        can_post: false,
        cannot_post_reason: 'rsvp_required',
      },
    });
    renderCard();
    await waitFor(() => {
      expect(screen.getByText(/rsvp to join the conversation/i)).toBeInTheDocument();
    });
    expect(screen.queryByText('leaked comment')).not.toBeInTheDocument();
  });

  it('shows the comment thread when the viewer can post', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        items: [
          {
            id: 'c1',
            author_id: 'other',
            author_display_name: 'someone',
            author_photo_url: '',
            body: 'visible comment',
            is_deleted: false,
            created_at: new Date().toISOString(),
            reactions: [],
            can_delete: false,
            replies: [],
          },
        ],
        can_post: true,
        cannot_post_reason: null,
      },
    });
    renderCard();
    await waitFor(() => {
      expect(screen.getByText('visible comment')).toBeInTheDocument();
    });
  });

  describe('live updates', () => {
    beforeEach(() => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [], can_post: true, cannot_post_reason: null },
      });
    });

    it('skips the scoped stream for members', async () => {
      renderCard('rsvp-tok');
      await screen.findByRole('button', { name: /post/i });
      expect(lastStreamOptions().eventScope).toBeNull();
    });

    it('opens an event-scoped stream for a logged-out rsvp viewer', async () => {
      authState.status = 'unauthed';
      renderCard('rsvp-tok');
      await screen.findByRole('button', { name: /post/i });
      expect(lastStreamOptions().eventScope).toEqual({ eventId, token: 'rsvp-tok' });
    });

    it('refetches comments only on pings for this event', async () => {
      authState.status = 'unauthed';
      renderCard('rsvp-tok');
      await screen.findByRole('button', { name: /post/i });
      const onUpdate = lastStreamOptions().events.event_updated!;
      const getCalls = () => vi.mocked(apiClient.get).mock.calls.length;
      const before = getCalls();

      onUpdate(new MessageEvent('event_updated', { data: 'not json' }));
      onUpdate(new MessageEvent('event_updated', { data: JSON.stringify({ event_id: 'other' }) }));
      onUpdate(new MessageEvent('event_updated', { data: JSON.stringify({ event_id: 7 }) }));
      onUpdate(new MessageEvent('event_updated', { data: 'null' }));
      expect(getCalls()).toBe(before);

      onUpdate(new MessageEvent('event_updated', { data: JSON.stringify({ event_id: eventId }) }));
      await waitFor(() => expect(getCalls()).toBe(before + 1));
    });
  });
});
