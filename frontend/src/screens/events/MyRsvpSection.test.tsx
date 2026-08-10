import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';
import { type Event, RsvpServerStatus } from '@/models/event';
import { makeEvent as makeBaseEvent, makeGuest, makeUser } from '@/test/fixtures';

import { MyRsvpSection } from './MyRsvpSection';

const setRsvpMutate = vi.hoisted(() => vi.fn());
const removeRsvpMutate = vi.hoisted(() => vi.fn());
vi.mock('@/api/rsvp', () => ({
  useSetRsvp: () => ({ mutateAsync: setRsvpMutate, isPending: false }),
  useRemoveRsvp: () => ({ mutateAsync: removeRsvpMutate, isPending: false }),
}));

const updatePublicRsvpMutate = vi.hoisted(() => vi.fn());
const cancelPublicRsvpMutate = vi.hoisted(() => vi.fn());
vi.mock('@/api/publicRsvp', () => ({
  useUpdatePublicMyRsvp: () => ({ mutateAsync: updatePublicRsvpMutate, isPending: false }),
  useCancelPublicMyRsvp: () => ({ mutateAsync: cancelPublicRsvpMutate, isPending: false }),
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

function renderSection(event: Event, token?: string, locked?: boolean) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <MyRsvpSection
          event={event}
          {...(token ? { token } : {})}
          {...(locked ? { locked } : {})}
        />
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

describe('MyRsvpSection — before RSVPing', () => {
  it('opens the RSVP box when the rsvp button is tapped (not yet RSVP’d)', () => {
    renderSection(makeEvent({ myRsvp: null }));

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'rsvp' }));

    expect(screen.getByRole('dialog', { name: /RSVP/i })).toBeInTheDocument();
  });

  it('shows a single rsvp button and no status line when I have not RSVP’d', () => {
    renderSection(makeEvent({ myRsvp: null }));

    expect(screen.getByRole('button', { name: 'rsvp' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: "i'm going" })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'maybe' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: "can't go" })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /edit RSVP/i })).not.toBeInTheDocument();
  });

  it('shows "join the waitlist" instead of "rsvp" when the event is full', () => {
    renderSection(makeEvent({ maxAttendees: 2, attendingCount: 2, myRsvp: null }));

    expect(screen.getByRole('button', { name: 'join the waitlist' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'rsvp' })).not.toBeInTheDocument();
  });

  it('opens the RSVP box defaulted to "going" when the rsvp button is tapped', () => {
    renderSection(makeEvent({ myRsvp: null }));

    fireEvent.click(screen.getByRole('button', { name: 'rsvp' }));

    expect(screen.getByRole('button', { name: "i'm going" })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });
});

describe('MyRsvpSection — after RSVPing', () => {
  it('shows an edit RSVP button and no status pills once the member has responded', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Attending }));

    expect(screen.queryByRole('button', { name: "i'm going" })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'maybe' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: "can't go" })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /edit RSVP/i })).toBeInTheDocument();
  });

  it('shows an "i\'m going" status badge when attending', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Attending }));
    expect(screen.getByText("i'm going")).toBeInTheDocument();
  });

  it('shows a "maybe" status badge when maybe', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Maybe }));
    expect(screen.getByText('maybe')).toBeInTheDocument();
  });

  it('shows an "i can\'t go" status badge when cant_go', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.CantGo }));
    expect(screen.getByText("i can't go")).toBeInTheDocument();
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

  it('shows the waitlist banner and an edit button (no pills, no status line)', () => {
    renderSection(
      makeEvent({
        myRsvp: RsvpServerStatus.Waitlisted,
        guests: [makeGuest({ userId: 'user-me', name: 'Me', status: RsvpServerStatus.Waitlisted })],
      }),
    );

    expect(screen.getByText("you're on the waitlist")).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'edit' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /edit RSVP/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: "i'm going" })).not.toBeInTheDocument();
    expect(screen.queryByText("you're going")).not.toBeInTheDocument();
  });

  it('lets a waitlisted member open the edit dialog and toggle +1 (Issue 1289)', () => {
    renderSection(
      makeEvent({
        myRsvp: RsvpServerStatus.Waitlisted,
        guests: [makeGuest({ userId: 'user-me', name: 'Me', status: RsvpServerStatus.Waitlisted })],
      }),
    );

    fireEvent.click(screen.getByRole('button', { name: 'edit' }));
    expect(screen.getByRole('dialog', { name: /RSVP/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /^add \+1$/i }));
    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    expect(setRsvpMutate).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpServerStatus.Waitlisted, hasPlusOne: true }),
    );
  });

  it('says "save", not "join the waitlist", when already waitlisted on a full event', () => {
    renderSection(
      makeEvent({
        myRsvp: RsvpServerStatus.Waitlisted,
        maxAttendees: 2,
        attendingCount: 2,
      }),
    );

    fireEvent.click(screen.getByRole('button', { name: 'edit' }));

    expect(screen.getByRole('button', { name: /^save$/i })).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /^join the waitlist$/i }),
    ).not.toBeInTheDocument();
  });
});

describe('MyRsvpSection — locked (past event)', () => {
  it('shows a past-tense status badge that is not clickable', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Attending }), undefined, true);

    expect(screen.getByText('you went')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /edit RSVP/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /you went/i })).not.toBeInTheDocument();
  });

  it('shows "you were a maybe" for a past maybe', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Maybe }), undefined, true);
    expect(screen.getByText('you were a maybe')).toBeInTheDocument();
  });

  it('shows "you couldn\'t go" for a past cant_go', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.CantGo }), undefined, true);
    expect(screen.getByText("you couldn't go")).toBeInTheDocument();
  });

  it('shows nothing when the member never rsvp’d', () => {
    renderSection(makeEvent({ myRsvp: null }), undefined, true);

    expect(screen.queryByRole('button', { name: 'rsvp' })).not.toBeInTheDocument();
    expect(screen.queryByText(/rsvp/i)).not.toBeInTheDocument();
  });

  it('shows nothing and no edit action for a locked waitlist entry', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Waitlisted }), undefined, true);

    expect(screen.queryByText(/waitlist/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'edit' })).not.toBeInTheDocument();
  });

  it('never opens the RSVP box when locked', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Attending }), undefined, true);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});

describe('MyRsvpSection — spots left indicator', () => {
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

describe('MyRsvpSection — spots left', () => {
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

describe('MyRsvpSection — leave waitlist error handling (issue #633)', () => {
  it('surfaces an error when leaving the waitlist fails', async () => {
    removeRsvpMutate.mockRejectedValue(new Error('boom'));
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Waitlisted }));

    fireEvent.click(screen.getByRole('button', { name: 'edit' }));
    fireEvent.click(screen.getByRole('button', { name: /remove rsvp/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/couldn't update your rsvp/i);
  });
});

describe('MyRsvpSection — token-holding viewer (Issue 854)', () => {
  it('shows the +1 toggle as "remove +1" using viewerUserId, not useAuthStore (no logged-in user)', () => {
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

    expect(screen.getByRole('button', { name: /^remove \+1$/i })).toBeInTheDocument();
  });
});

describe('MyRsvpSection — comments in public manage vs member flows', () => {
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

    fireEvent.click(screen.getByRole('button', { name: 'rsvp' }));
    expect(screen.getByTestId('rsvp-comment-field')).toBeInTheDocument();
  });
});
