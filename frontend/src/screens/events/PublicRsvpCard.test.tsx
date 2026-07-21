import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { type Event, RsvpServerStatus } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

const updateMutate = vi.fn();
const cancelMutate = vi.fn();
vi.mock('@/api/publicRsvp', () => ({
  useUpdatePublicMyRsvp: () => ({ mutateAsync: updateMutate, isPending: false }),
  useCancelPublicMyRsvp: () => ({ mutateAsync: cancelMutate, isPending: false }),
}));

import { PublicRsvpCard } from './PublicRsvpCard';

function renderCard(props: { status: string; event?: Partial<Event> }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <PublicRsvpCard
          token="tok123"
          event={makeEvent({ allowPlusOnes: true, ...props.event })}
          status={props.status}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('PublicRsvpCard', () => {
  it('links the event title to the event detail page', () => {
    renderCard({
      status: RsvpServerStatus.Attending,
      event: { id: 'ev1', title: 'Potluck' },
    });
    expect(screen.getByRole('link', { name: 'Potluck' })).toHaveAttribute('href', '/events/ev1');
  });

  it('never shows a +1 toggle — non-members cannot bring a +1', () => {
    renderCard({ status: RsvpServerStatus.Attending });
    expect(screen.queryByRole('switch', { name: /bring a \+1/i })).not.toBeInTheDocument();
  });

  it('sends has_plus_one false when changing status', () => {
    renderCard({ status: RsvpServerStatus.Attending });
    fireEvent.click(screen.getByRole('button', { name: /^maybe$/i }));
    expect(updateMutate).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpServerStatus.Maybe, hasPlusOne: false }),
    );
  });

  it('renders the comment field', () => {
    renderCard({ status: RsvpServerStatus.Attending });
    expect(screen.getByLabelText('comment (optional)')).toBeInTheDocument();
  });

  it('calls update with the comment when save comment is clicked', async () => {
    updateMutate.mockResolvedValue(undefined);
    renderCard({ status: RsvpServerStatus.Attending });
    fireEvent.change(screen.getByLabelText('comment (optional)'), {
      target: { value: 'bringing snacks' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'save comment' }));
    await waitFor(() => expect(updateMutate).toHaveBeenCalled());
    expect(updateMutate).toHaveBeenCalledWith(
      expect.objectContaining({ comment: 'bringing snacks' }),
    );
  });
});
