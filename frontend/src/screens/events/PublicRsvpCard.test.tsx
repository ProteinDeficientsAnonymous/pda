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

function renderCard(props: { status: string; hasPlusOne: boolean; event?: Partial<Event> }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <PublicRsvpCard
          token="tok123"
          event={makeEvent({ allowPlusOnes: true, ...props.event })}
          status={props.status}
          hasPlusOne={props.hasPlusOne}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('PublicRsvpCard', () => {
  it('links the event title to the event detail page', () => {
    renderCard({
      status: RsvpServerStatus.Attending,
      hasPlusOne: false,
      event: { id: 'ev1', title: 'Potluck' },
    });
    expect(screen.getByRole('link', { name: 'Potluck' })).toHaveAttribute('href', '/events/ev1');
  });

  it('shows the +1 toggle when attending', () => {
    renderCard({ status: RsvpServerStatus.Attending, hasPlusOne: false });
    expect(screen.getByRole('switch', { name: /bring a \+1/i })).toBeInTheDocument();
  });

  it('keeps the +1 toggle visible and checked after switching to maybe', () => {
    renderCard({ status: RsvpServerStatus.Attending, hasPlusOne: true });
    fireEvent.click(screen.getByRole('button', { name: /^maybe$/i }));
    expect(updateMutate).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpServerStatus.Maybe, hasPlusOne: true }),
    );
  });

  it('preserves the +1 flag when switching to can’t go', () => {
    renderCard({ status: RsvpServerStatus.Attending, hasPlusOne: true });
    fireEvent.click(screen.getByRole('button', { name: /can't go/i }));
    expect(updateMutate).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpServerStatus.CantGo, hasPlusOne: true }),
    );
  });

  it('allows toggling +1 while on maybe', () => {
    renderCard({ status: RsvpServerStatus.Maybe, hasPlusOne: false });
    fireEvent.click(screen.getByRole('switch', { name: /bring a \+1/i }));
    expect(updateMutate).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpServerStatus.Maybe, hasPlusOne: true }),
    );
  });

  it('hides the +1 toggle when waitlisted', () => {
    renderCard({ status: RsvpServerStatus.Waitlisted, hasPlusOne: false });
    expect(screen.queryByRole('switch', { name: /bring a \+1/i })).not.toBeInTheDocument();
  });

  it('hides the +1 toggle when the event does not allow plus ones', () => {
    renderCard({
      status: RsvpServerStatus.Attending,
      hasPlusOne: false,
      event: { allowPlusOnes: false },
    });
    expect(screen.queryByRole('switch', { name: /bring a \+1/i })).not.toBeInTheDocument();
  });

  it('renders the comment field', () => {
    renderCard({ status: RsvpServerStatus.Attending, hasPlusOne: false });
    expect(screen.getByLabelText('comment (optional)')).toBeInTheDocument();
  });

  it('calls update with the comment when save comment is clicked', async () => {
    updateMutate.mockResolvedValue(undefined);
    renderCard({ status: RsvpServerStatus.Attending, hasPlusOne: false });
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
