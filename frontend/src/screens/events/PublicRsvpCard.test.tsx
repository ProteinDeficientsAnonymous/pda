import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { type Event, RsvpServerStatus } from '@/models/event';
import { makeEvent, makePaidEvent } from '@/test/fixtures';

import { PublicRsvpCard } from './PublicRsvpCard';

const updateMutate = vi.hoisted(() => vi.fn());
const cancelMutate = vi.hoisted(() => vi.fn());
vi.mock('@/api/publicRsvp', () => ({
  useUpdatePublicMyRsvp: () => ({ mutateAsync: updateMutate, isPending: false }),
  useCancelPublicMyRsvp: () => ({ mutateAsync: cancelMutate, isPending: false }),
}));

const mockUseFlag = vi.hoisted(() => vi.fn(() => true));
vi.mock('@/api/featureFlags', () => ({ useFlag: mockUseFlag }));

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
  beforeEach(() => {
    updateMutate.mockReset();
    cancelMutate.mockReset();
    mockUseFlag.mockReset();
    mockUseFlag.mockReturnValue(true);
  });

  it('links the event title to the event detail page', () => {
    renderCard({
      status: RsvpServerStatus.Attending,
      event: { id: 'ev1', slug: 'potluck', title: 'Potluck' },
    });
    expect(screen.getByRole('link', { name: 'Potluck' })).toHaveAttribute(
      'href',
      '/events/potluck',
    );
  });

  it('falls back to the event id when the event has no slug', () => {
    renderCard({
      status: RsvpServerStatus.Attending,
      event: { id: 'ev1', slug: '', title: 'Potluck' },
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

describe('PublicRsvpCard payment confirmation gate', () => {
  const { price, venmoLink } = makePaidEvent();
  const paidEventOverrides: Partial<Event> = { price, venmoLink };

  beforeEach(() => {
    updateMutate.mockReset();
    cancelMutate.mockReset();
    mockUseFlag.mockReset();
    mockUseFlag.mockReturnValue(true);
  });

  it('shows the payment step before switching to attending on a paid event', () => {
    mockUseFlag.mockReturnValue(true);
    renderCard({ status: RsvpServerStatus.Maybe, event: paidEventOverrides });
    fireEvent.click(screen.getByRole('button', { name: /^i'm going$/i }));
    expect(updateMutate).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /yes, i paid/i })).toBeInTheDocument();
  });

  it('submits with paidConfirmed after the payment step', async () => {
    mockUseFlag.mockReturnValue(true);
    updateMutate.mockResolvedValue(undefined);
    renderCard({ status: RsvpServerStatus.Maybe, event: paidEventOverrides });
    fireEvent.click(screen.getByRole('button', { name: /^i'm going$/i }));
    fireEvent.click(screen.getByRole('button', { name: /yes, i paid/i }));
    await waitFor(() => expect(updateMutate).toHaveBeenCalled());
    expect(updateMutate).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpServerStatus.Attending, paidConfirmed: true }),
    );
  });

  it('returns to the status picker from the payment step', () => {
    mockUseFlag.mockReturnValue(true);
    renderCard({ status: RsvpServerStatus.Maybe, event: paidEventOverrides });
    fireEvent.click(screen.getByRole('button', { name: /^i'm going$/i }));
    fireEvent.click(screen.getByRole('button', { name: /back/i }));
    expect(screen.getByRole('button', { name: /^i'm going$/i })).toBeInTheDocument();
    expect(updateMutate).not.toHaveBeenCalled();
  });

  it('does not gate switching to maybe', () => {
    mockUseFlag.mockReturnValue(true);
    renderCard({ status: RsvpServerStatus.Attending, event: paidEventOverrides });
    fireEvent.click(screen.getByRole('button', { name: /^maybe$/i }));
    expect(updateMutate).toHaveBeenCalledOnce();
  });

  it('does not gate saving a comment while already attending', async () => {
    mockUseFlag.mockReturnValue(true);
    updateMutate.mockResolvedValue(undefined);
    renderCard({ status: RsvpServerStatus.Attending, event: paidEventOverrides });
    fireEvent.change(screen.getByLabelText('comment (optional)'), {
      target: { value: 'see you there' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'save comment' }));
    await waitFor(() => expect(updateMutate).toHaveBeenCalled());
  });

  it('does not gate on a free event', () => {
    mockUseFlag.mockReturnValue(true);
    renderCard({ status: RsvpServerStatus.Maybe });
    fireEvent.click(screen.getByRole('button', { name: /^i'm going$/i }));
    expect(updateMutate).toHaveBeenCalledOnce();
  });

  it('does not gate when the flag is off', () => {
    mockUseFlag.mockReturnValue(false);
    renderCard({ status: RsvpServerStatus.Maybe, event: paidEventOverrides });
    fireEvent.click(screen.getByRole('button', { name: /^i'm going$/i }));
    expect(updateMutate).toHaveBeenCalledOnce();
  });
});
