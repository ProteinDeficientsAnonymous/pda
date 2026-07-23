import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { toast } from 'sonner';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { RsvpServerStatus } from '@/models/event';
import { makeEvent, makeGuest } from '@/test/fixtures';

const setGuestRsvpMutate = vi.fn();
const removeGuestRsvpMutate = vi.fn();
vi.mock('@/api/eventStats', () => ({
  useSetGuestRsvp: () => ({ mutate: setGuestRsvpMutate, isPending: false }),
  useRemoveGuestRsvp: () => ({ mutate: removeGuestRsvpMutate, isPending: false }),
}));
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));
vi.mock('@/api/userSearch', () => ({
  useUserSearch: () => ({
    data: [{ id: 'new-1', fullName: 'New Member', phoneNumber: '+15551234567' }],
  }),
}));

import { EventManageRsvpsPanel } from './EventManageRsvpsPanel';

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
});
