import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('@/auth/store', () => {
  const state = {
    status: 'authed',
    user: { id: 'u-me', displayName: 'Me', profilePhotoUrl: null },
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
import { apiClient } from '@/api/client';

import { EventCommentsCard } from './EventCommentsCard';

const eventId = '11111111-1111-1111-1111-111111111111';

function renderCard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <EventCommentsCard eventId={eventId} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
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
});
