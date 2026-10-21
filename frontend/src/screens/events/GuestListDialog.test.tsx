import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { RsvpServerStatus } from '@/models/event';
import { makeEvent, makeGuest } from '@/test/fixtures';

import { GuestListDialog } from './GuestListDialog';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), put: vi.fn() },
  setAuthBridge: vi.fn(),
}));
vi.mock('sonner', () => ({ toast: { error: vi.fn() } }));
vi.mock('@/components/SortableList', () => ({
  SortableList: ({
    items,
    onReorder,
    renderItem,
    ariaLabel,
  }: {
    items: { id: string }[];
    onReorder: (ids: string[]) => void;
    renderItem: (item: { id: string }) => ReactNode;
    ariaLabel?: string;
  }) => (
    <div>
      <ul aria-label={ariaLabel}>
        {items.map((item) => (
          <li key={item.id}>{renderItem(item)}</li>
        ))}
      </ul>
      <button
        type="button"
        onClick={() => {
          onReorder(items.map((i) => i.id).reverse());
        }}
      >
        mock drop: reverse
      </button>
    </div>
  ),
}));

const event = makeEvent({
  id: 'ev1',
  guests: [
    makeGuest({ userId: 'a1', name: 'Pat', status: RsvpServerStatus.Attending }),
    makeGuest({ userId: 'w1', name: 'Alex', status: RsvpServerStatus.Waitlisted }),
    makeGuest({ userId: 'w2', name: 'Sam', status: RsvpServerStatus.Waitlisted }),
  ],
});

function renderDialog(canReorderWaitlist: boolean) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <GuestListDialog
          event={event}
          canSeeInvited
          canReorderWaitlist={canReorderWaitlist}
          initialTab="waitlist"
          onClose={vi.fn()}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(apiClient.get).mockResolvedValue({
    data: { guests: [], invited_user_ids: [], invited_user_names: [], invited_user_photo_urls: [] },
  });
  vi.mocked(apiClient.put).mockReset();
  vi.mocked(apiClient.put).mockResolvedValue({ data: {} });
});

describe('GuestListDialog waitlist reorder', () => {
  it('lets a host drag the waitlist and saves the new order', async () => {
    renderDialog(true);
    expect(screen.getByRole('list', { name: 'waitlist order' })).toHaveTextContent(/Alex.*Sam/);
    await userEvent.click(screen.getByRole('button', { name: 'mock drop: reverse' }));
    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalledWith('/api/community/events/ev1/waitlist/order/', {
        user_ids: ['w2', 'w1'],
      });
    });
  });

  it('is not draggable without reorder rights', () => {
    renderDialog(false);
    expect(screen.queryByRole('list', { name: 'waitlist order' })).not.toBeInTheDocument();
    expect(screen.getByText('Alex')).toBeInTheDocument();
  });

  it('turns off dragging while searching', async () => {
    renderDialog(true);
    await userEvent.type(screen.getByPlaceholderText('search guests'), 'al');
    expect(screen.queryByRole('list', { name: 'waitlist order' })).not.toBeInTheDocument();
  });
});
