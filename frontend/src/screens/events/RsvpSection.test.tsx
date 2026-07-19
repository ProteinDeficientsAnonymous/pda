import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';
import { type Event, RsvpServerStatus } from '@/models/event';
import { makeEvent as makeBaseEvent, makeGuest, makeUser } from '@/test/fixtures';

const setRsvpMutate = vi.fn();
const removeRsvpMutate = vi.fn();
vi.mock('@/api/rsvp', () => ({
  useSetRsvp: () => ({ mutateAsync: setRsvpMutate, isPending: false }),
  useRemoveRsvp: () => ({ mutateAsync: removeRsvpMutate, isPending: false }),
}));

const updatePublicRsvpMutate = vi.fn();
const cancelPublicRsvpMutate = vi.fn();
vi.mock('@/api/publicRsvp', () => ({
  useUpdatePublicMyRsvp: () => ({ mutateAsync: updatePublicRsvpMutate, isPending: false }),
  useCancelPublicMyRsvp: () => ({ mutateAsync: cancelPublicRsvpMutate, isPending: false }),
}));

vi.mock('./RsvpGuestList', () => ({
  RsvpGuestList: () => <div data-testid="guest-list" />,
}));

// Covered by RsvpCommentField.test.tsx — stubbed here so the RsvpBox's textarea
// isn't a factor in assertions that only care about the dialog/pills.
vi.mock('./RsvpCommentField', () => ({
  RsvpCommentField: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <textarea
      data-testid="rsvp-comment-field"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}));

import { RsvpSection } from './RsvpSection';

const ME = makeUser({ id: 'user-me', firstName: 'Me', lastName: '', fullName: 'Me' });

function makeEvent(overrides: Partial<Event> = {}): Event {
  return makeBaseEvent({
    createdById: 'user-host',
    createdByName: 'Host',
    allowPlusOnes: true,
    guests: [],
    ...overrides,
  });
}

function renderSection(event: Event, token?: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <RsvpSection event={event} canSeeInvited={false} {...(token ? { token } : {})} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  setRsvpMutate.mockReset();
  setRsvpMutate.mockResolvedValue(undefined);
  removeRsvpMutate.mockReset();
  removeRsvpMutate.mockResolvedValue(undefined);
  useAuthStore.setState({ status: 'authed', user: ME, accessToken: 'tok' });
});

describe('RsvpSection — before RSVPing', () => {
  it('opens the RSVP box when a pill is tapped (not yet RSVP’d)', () => {
    renderSection(makeEvent({ myRsvp: null }));

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: "i'm going" }));

    expect(screen.getByRole('dialog', { name: /RSVP/i })).toBeInTheDocument();
  });

  it('shows all three pills and no status line when I have not RSVP’d', () => {
    renderSection(makeEvent({ myRsvp: null }));

    expect(screen.getByRole('button', { name: "i'm going" })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'maybe' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: "can't go" })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /edit RSVP/i })).not.toBeInTheDocument();
  });

  it('shows "join the waitlist" instead of "i\'m going" when the event is full', () => {
    renderSection(makeEvent({ maxAttendees: 2, attendingCount: 2, myRsvp: null }));

    expect(screen.getByRole('button', { name: 'join the waitlist' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: "i'm going" })).not.toBeInTheDocument();
  });
});

describe('RsvpSection — after RSVPing', () => {
  it('shows an edit RSVP button and no status pills once the member has responded', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Attending }));

    expect(screen.queryByRole('button', { name: "i'm going" })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'maybe' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: "can't go" })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /edit RSVP/i })).toBeInTheDocument();
  });

  it('shows a "you\'re going" status line when attending', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Attending }));
    expect(screen.getByText("you're going")).toBeInTheDocument();
  });

  it('shows a "you\'re a maybe" status line when maybe', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Maybe }));
    expect(screen.getByText("you're a maybe")).toBeInTheDocument();
  });

  it('shows a "you can\'t go" status line when cant_go', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.CantGo }));
    expect(screen.getByText("you can't go")).toBeInTheDocument();
  });

  it('opens the RSVP box in edit mode when "edit RSVP" is tapped', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Attending }));

    fireEvent.click(screen.getByRole('button', { name: /edit RSVP/i }));

    expect(screen.getByRole('dialog', { name: /RSVP/i })).toBeInTheDocument();
  });

  it('removes the RSVP when "remove rsvp" is tapped in the edit box', async () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Attending }));

    fireEvent.click(screen.getByRole('button', { name: /edit RSVP/i }));
    fireEvent.click(screen.getByRole('button', { name: /remove rsvp/i }));

    expect(removeRsvpMutate).toHaveBeenCalledWith('ev1');
  });

  it('shows only "leave waitlist" when on the waitlist (no pills, no status line, no edit button)', () => {
    renderSection(
      makeEvent({
        myRsvp: RsvpServerStatus.Waitlisted,
        guests: [makeGuest({ userId: 'user-me', name: 'Me', status: RsvpServerStatus.Waitlisted })],
      }),
    );

    expect(screen.getByRole('button', { name: 'leave waitlist' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /edit RSVP/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: "i'm going" })).not.toBeInTheDocument();
  });
});

describe('RsvpSection — spots left indicator', () => {
  it('shows spots left when the event has a cap and room remains', () => {
    renderSection(makeEvent({ maxAttendees: 4, attendingCount: 2, myRsvp: null }));
    expect(screen.getByText('2 spots left')).toBeInTheDocument();
  });

  it('hides spots left when uncapped', () => {
    renderSection(makeEvent({ maxAttendees: null, attendingCount: 2, myRsvp: null }));
    expect(screen.queryByText(/spots left/)).not.toBeInTheDocument();
  });

  it('hides spots left at capacity', () => {
    renderSection(makeEvent({ maxAttendees: 2, attendingCount: 2, myRsvp: null }));
    expect(screen.queryByText(/spots left/)).not.toBeInTheDocument();
  });
});

describe('RsvpSection — spots left', () => {
  it('shows "x spots left" for a capacity-limited event with room', () => {
    renderSection(makeEvent({ maxAttendees: 10, attendingCount: 7, myRsvp: null }));
    expect(screen.getByText('3 spots left')).toBeInTheDocument();
  });

  it('singularizes "1 spot left"', () => {
    renderSection(makeEvent({ maxAttendees: 10, attendingCount: 9, myRsvp: null }));
    expect(screen.getByText('1 spot left')).toBeInTheDocument();
  });

  it('shows no spots-left text for unlimited-capacity events', () => {
    renderSection(makeEvent({ maxAttendees: null, attendingCount: 7, myRsvp: null }));
    expect(screen.queryByText(/spots? left/)).not.toBeInTheDocument();
  });

  it('shows no spots-left text at capacity', () => {
    renderSection(makeEvent({ maxAttendees: 10, attendingCount: 10, myRsvp: null }));
    expect(screen.queryByText(/spots? left/)).not.toBeInTheDocument();
  });
});

describe('RsvpSection — leave waitlist error handling (issue #633)', () => {
  it('surfaces an error when leaving the waitlist fails', async () => {
    removeRsvpMutate.mockRejectedValue(new Error('boom'));
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Waitlisted }));

    fireEvent.click(screen.getByRole('button', { name: 'leave waitlist' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/couldn't update your rsvp/i);
  });
});

describe('RsvpSection — token-holding viewer (Issue 854)', () => {
  it('shows the +1 toggle checked using viewerUserId, not useAuthStore (no logged-in user)', () => {
    useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
    renderSection(
      makeEvent({
        myRsvp: RsvpServerStatus.Attending,
        viewerUserId: 'non-member-1',
        guests: [
          makeGuest({ userId: 'non-member-1', name: 'Non Member', hasPlusOne: true }),
          makeGuest({ userId: 'user-other', name: 'Other', hasPlusOne: false }),
        ],
      }),
      'tok-abc',
    );

    fireEvent.click(screen.getByRole('button', { name: /edit RSVP/i }));

    expect(screen.getByRole('checkbox')).toBeChecked();
  });
});

describe('RsvpSection — comments in public manage vs member flows', () => {
  beforeEach(() => {
    updatePublicRsvpMutate.mockReset();
    setRsvpMutate.mockReset();
  });

  it('renders the comment field in edit mode when token is present, and forwards it on save', async () => {
    useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
    renderSection(
      makeEvent({
        myRsvp: RsvpServerStatus.Attending,
        viewerUserId: 'nonmember-1',
      }),
      'tok-123',
    );

    fireEvent.click(screen.getByRole('button', { name: /edit RSVP/i }));
    const commentField = screen.getByTestId('rsvp-comment-field');
    expect(commentField).toBeInTheDocument();
    fireEvent.change(commentField, { target: { value: 'bringing snacks' } });

    fireEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(updatePublicRsvpMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        comment: 'bringing snacks',
      }),
    );
  });

  it('hides the comment field in edit mode when token is absent (member edit)', () => {
    useAuthStore.setState({ status: 'authed', user: ME, accessToken: 'abc' });
    renderSection(
      makeEvent({
        myRsvp: RsvpServerStatus.Attending,
      }),
    );

    fireEvent.click(screen.getByRole('button', { name: /edit RSVP/i }));
    expect(screen.queryByTestId('rsvp-comment-field')).not.toBeInTheDocument();
  });

  it('shows the comment field in create mode when token is absent (member create)', () => {
    useAuthStore.setState({ status: 'authed', user: ME, accessToken: 'abc' });
    renderSection(
      makeEvent({
        myRsvp: null,
      }),
    );

    fireEvent.click(screen.getByRole('button', { name: /going/i }));
    expect(screen.getByTestId('rsvp-comment-field')).toBeInTheDocument();
  });
});
