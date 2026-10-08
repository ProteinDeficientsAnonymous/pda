import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { toast } from 'sonner';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { RsvpServerStatus } from '@/models/event';
import { makeEvent, makeGuest } from '@/test/fixtures';

import { EventManageRsvpsPanel } from './EventManageRsvpsPanel';

const setGuestRsvpMutate = vi.hoisted(() => vi.fn());
const removeGuestRsvpMutate = vi.hoisted(() => vi.fn());
const setGuestPaymentMutate = vi.hoisted(() => vi.fn());
const reorderWaitlistMutate = vi.hoisted(() => vi.fn());
vi.mock('@/api/eventStats', () => ({
  useSetGuestRsvp: () => ({ mutate: setGuestRsvpMutate, isPending: false }),
  useRemoveGuestRsvp: () => ({ mutate: removeGuestRsvpMutate, isPending: false }),
  useSetGuestPayment: () => ({ mutate: setGuestPaymentMutate, isPending: false }),
  useReorderWaitlist: () => ({ mutate: reorderWaitlistMutate, isPending: false }),
}));
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
          const ids = items.map((i) => i.id);
          onReorder([...ids.slice(-1), ...ids.slice(0, -1)]);
        }}
      >
        mock drop: move last to top
      </button>
    </div>
  ),
}));
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));
vi.mock('@/api/userSearch', () => ({
  useUserSearch: () => ({
    data: [{ id: 'new-1', fullName: 'New Member', phoneNumber: '+15551234567' }],
  }),
}));

function renderPanel(event = makeEvent({})) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <EventManageRsvpsPanel event={event} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  setGuestRsvpMutate.mockReset();
  removeGuestRsvpMutate.mockReset();
  setGuestPaymentMutate.mockReset();
  reorderWaitlistMutate.mockReset();
  vi.mocked(toast.error).mockReset();
});

describe('EventManageRsvpsPanel', () => {
  it('groups guests by status', () => {
    renderPanel(
      makeEvent({
        guests: [
          makeGuest({ userId: 'u1', name: 'Alex', status: RsvpServerStatus.Attending }),
          makeGuest({ userId: 'u2', name: 'Sam', status: RsvpServerStatus.Maybe }),
        ],
      }),
    );
    expect(screen.getByText('Alex')).toBeInTheDocument();
    expect(screen.getByText('Sam')).toBeInTheDocument();
  });

  it('changes a guest status via the picker', () => {
    renderPanel(
      makeEvent({
        guests: [makeGuest({ userId: 'u1', name: 'Alex', status: RsvpServerStatus.Attending })],
      }),
    );
    fireEvent.click(screen.getByRole('button', { name: /^maybe$/i }));
    expect(setGuestRsvpMutate).toHaveBeenCalledWith(
      { userId: 'u1', status: 'maybe', hasPlusOne: false },
      expect.objectContaining({ onError: expect.any(Function) }),
    );
  });

  it('toggles a guest +1', () => {
    renderPanel(
      makeEvent({
        guests: [
          makeGuest({
            userId: 'u1',
            name: 'Alex',
            status: RsvpServerStatus.Attending,
            hasPlusOne: false,
          }),
        ],
      }),
    );
    fireEvent.click(screen.getByRole('button', { name: /add \+1/i }));
    expect(setGuestRsvpMutate).toHaveBeenCalledWith(
      { userId: 'u1', status: 'attending', hasPlusOne: true },
      expect.objectContaining({ onError: expect.any(Function) }),
    );
  });

  it('removes a guest', () => {
    renderPanel(
      makeEvent({
        guests: [makeGuest({ userId: 'u1', name: 'Alex', status: RsvpServerStatus.Attending })],
      }),
    );
    fireEvent.click(screen.getByRole('button', { name: /remove alex/i }));
    expect(removeGuestRsvpMutate).toHaveBeenCalledWith(
      { userId: 'u1' },
      expect.objectContaining({ onError: expect.any(Function) }),
    );
  });

  it('does not show edit controls for non-member guests', () => {
    renderPanel(
      makeEvent({
        guests: [
          makeGuest({
            userId: 'u1',
            name: 'Walkin',
            status: RsvpServerStatus.Attending,
            isMember: false,
          }),
        ],
      }),
    );
    expect(screen.queryByRole('button', { name: /remove walkin/i })).not.toBeInTheDocument();
  });

  it('shows an empty state with no guests', () => {
    renderPanel(makeEvent({ guests: [] }));
    expect(screen.getByText(/no one yet/i)).toBeInTheDocument();
  });

  it('adds a member via the picker', () => {
    renderPanel(makeEvent({ guests: [] }));
    fireEvent.change(screen.getByLabelText(/add a member/i), { target: { value: 'new' } });
    fireEvent.click(screen.getByRole('button', { name: /new member/i }));
    fireEvent.click(screen.getByRole('button', { name: /^add$/i }));
    expect(setGuestRsvpMutate).toHaveBeenCalledWith(
      { userId: 'new-1', status: 'attending', hasPlusOne: false },
      expect.objectContaining({ onError: expect.any(Function) }),
    );
  });

  it('excludes existing guests from the add-member search results', () => {
    renderPanel(
      makeEvent({
        guests: [
          makeGuest({ userId: 'new-1', name: 'New Member', status: RsvpServerStatus.Attending }),
        ],
      }),
    );
    fireEvent.change(screen.getByLabelText(/add a member/i), { target: { value: 'new' } });
    expect(screen.queryByRole('button', { name: /^new member/i })).not.toBeInTheDocument();
  });

  it('does not show a paid indicator for events that do not require payment', () => {
    renderPanel(
      makeEvent({
        price: '',
        guests: [makeGuest({ userId: 'u1', name: 'Alex', status: RsvpServerStatus.Attending })],
      }),
    );
    expect(screen.queryByText(/unpaid/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^paid$/i)).not.toBeInTheDocument();
  });

  it('shows an unpaid indicator for a paid event guest who has not confirmed', () => {
    renderPanel(
      makeEvent({
        price: '$10',
        venmoLink: 'https://venmo.com/u/host',
        guests: [
          makeGuest({
            userId: 'u1',
            name: 'Alex',
            status: RsvpServerStatus.Attending,
            paidConfirmed: false,
          }),
        ],
      }),
    );
    expect(screen.getByRole('button', { name: /unpaid/i })).toBeInTheDocument();
  });

  it('shows a paid indicator for a paid event guest who has confirmed', () => {
    renderPanel(
      makeEvent({
        price: '$10',
        venmoLink: 'https://venmo.com/u/host',
        guests: [
          makeGuest({
            userId: 'u1',
            name: 'Alex',
            status: RsvpServerStatus.Attending,
            paidConfirmed: true,
          }),
        ],
      }),
    );
    expect(screen.getByRole('button', { name: /^✓ paid$/i })).toBeInTheDocument();
  });

  it('toggles a guest payment status when the indicator is clicked', () => {
    renderPanel(
      makeEvent({
        price: '$10',
        venmoLink: 'https://venmo.com/u/host',
        guests: [
          makeGuest({
            userId: 'u1',
            name: 'Alex',
            status: RsvpServerStatus.Attending,
            paidConfirmed: false,
          }),
        ],
      }),
    );
    fireEvent.click(screen.getByRole('button', { name: /unpaid/i }));
    expect(setGuestPaymentMutate).toHaveBeenCalledWith(
      { userId: 'u1', paidConfirmed: true },
      expect.objectContaining({ onError: expect.any(Function) }),
    );
  });

  it('shows a paid indicator for non-member guests on a paid event', () => {
    renderPanel(
      makeEvent({
        price: '$10',
        venmoLink: 'https://venmo.com/u/host',
        guests: [
          makeGuest({
            userId: 'u1',
            name: 'Walkin',
            status: RsvpServerStatus.Attending,
            isMember: false,
            paidConfirmed: true,
          }),
        ],
      }),
    );
    expect(screen.getByRole('button', { name: /^✓ paid$/i })).toBeInTheDocument();
  });

  describe('waitlist order', () => {
    const waitlistEvent = () =>
      makeEvent({
        guests: [
          makeGuest({ userId: 'u0', name: 'Pat', status: RsvpServerStatus.Attending }),
          makeGuest({ userId: 'w1', name: 'Alex', status: RsvpServerStatus.Waitlisted }),
          makeGuest({ userId: 'w2', name: 'Sam', status: RsvpServerStatus.Waitlisted }),
          makeGuest({
            userId: 'w3',
            name: 'Jo',
            status: RsvpServerStatus.Waitlisted,
            isMember: false,
          }),
        ],
      });

    it('reorders the waitlist on drop', () => {
      renderPanel(waitlistEvent());
      const list = screen.getByRole('list', { name: 'waitlisted order' });
      expect(list).toHaveTextContent(/Alex.*Sam.*Jo/);
      fireEvent.click(screen.getByRole('button', { name: 'mock drop: move last to top' }));
      expect(reorderWaitlistMutate).toHaveBeenCalledWith(
        { userIds: ['w3', 'w1', 'w2'] },
        expect.objectContaining({ onError: expect.any(Function) }),
      );
    });

    it('only makes the waitlist draggable', () => {
      renderPanel(waitlistEvent());
      expect(screen.getAllByRole('list', { name: /order$/ })).toHaveLength(1);
    });
  });
});
