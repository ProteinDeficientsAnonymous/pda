import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Event } from '@/models/event';
import { RsvpServerStatus } from '@/models/event';
import { makeEvent, makeGuest } from '@/test/fixtures';

const setGuestRsvpMutate = vi.fn();
vi.mock('@/api/eventStats', () => ({
  useSetGuestRsvp: () => ({ mutate: setGuestRsvpMutate, isPending: false }),
}));

import { RsvpGuestList } from './RsvpGuestList';

function renderList(event: Event, canManageRsvps = false) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <RsvpGuestList event={event} canSeeInvited={false} canManageRsvps={canManageRsvps} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  setGuestRsvpMutate.mockReset();
});

describe('RsvpGuestList', () => {
  it('links member guests to their profile', () => {
    const event = makeEvent({
      guests: [makeGuest({ userId: 'user-1', name: 'Alex', isMember: true })],
    });
    renderList(event);
    const link = screen.getByRole('link', { name: /alex/i });
    expect(link).toHaveAttribute('href', '/members/user-1');
  });

  it('renders non-member guests without a profile link', () => {
    const event = makeEvent({
      guests: [makeGuest({ userId: 'guest-1', name: 'Sam', isMember: false, hasPlusOne: true })],
    });
    renderList(event);
    expect(screen.queryByRole('link', { name: /sam/i })).not.toBeInTheDocument();
    expect(screen.getByText('Sam')).toBeInTheDocument();
  });
});

describe('RsvpGuestList — cant go / waitlist visibility (Issue 1042)', () => {
  it('hides the cant go and waitlist tabs from a guest', () => {
    const event = makeEvent({
      guests: [
        makeGuest({ userId: 'user-1', status: RsvpServerStatus.CantGo }),
        makeGuest({ userId: 'user-2', status: RsvpServerStatus.Waitlisted }),
      ],
    });
    renderList(event, false);
    expect(screen.queryByRole('tab', { name: /can't go/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /waitlist/i })).not.toBeInTheDocument();
  });

  it('shows the cant go and waitlist tabs to a host', () => {
    const event = makeEvent({
      guests: [
        makeGuest({ userId: 'user-1', status: RsvpServerStatus.CantGo }),
        makeGuest({ userId: 'user-2', status: RsvpServerStatus.Waitlisted }),
      ],
    });
    renderList(event, true);
    expect(screen.getByRole('tab', { name: /can't go/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /waitlist/i })).toBeInTheDocument();
  });
});

describe('RsvpGuestList — host rsvp management (Issue 872)', () => {
  it('does not show an edit control when the viewer cannot manage rsvps', () => {
    renderList(makeEvent({ guests: [makeGuest({})] }), false);
    expect(screen.queryByRole('button', { name: /change other's rsvp/i })).not.toBeInTheDocument();
  });

  it('shows an edit control per guest when the viewer can manage rsvps', () => {
    renderList(makeEvent({ guests: [makeGuest({})] }), true);
    expect(screen.getByRole('button', { name: /change other's rsvp/i })).toBeInTheDocument();
  });

  it('does not show an edit control for non-member guests', () => {
    renderList(makeEvent({ guests: [makeGuest({ isMember: false })] }), true);
    expect(screen.queryByRole('button', { name: /change other's rsvp/i })).not.toBeInTheDocument();
  });

  it('opens a dialog with status options when edit is tapped', () => {
    renderList(makeEvent({ guests: [makeGuest({})] }), true);
    fireEvent.click(screen.getByRole('button', { name: /change other's rsvp/i }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^maybe$/i })).toBeInTheDocument();
  });

  it('calls the mutation with the selected status', () => {
    renderList(makeEvent({ guests: [makeGuest({})] }), true);
    fireEvent.click(screen.getByRole('button', { name: /change other's rsvp/i }));
    fireEvent.click(screen.getByRole('button', { name: /^maybe$/i }));
    expect(setGuestRsvpMutate).toHaveBeenCalledWith(
      { userId: 'user-other', status: 'maybe', hasPlusOne: false },
      expect.objectContaining({ onSuccess: expect.any(Function), onError: expect.any(Function) }),
    );
  });
});
