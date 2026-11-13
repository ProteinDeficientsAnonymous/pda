import { fireEvent, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { type Event, RsvpServerStatus, RsvpStatus } from '@/models/event';
import { setAuthed } from '@/test/auth';
import { makeEvent as makeBaseEvent, makeUser } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import { MyRsvpSection } from './MyRsvpSection';

const setRsvpMutate = vi.hoisted(() => vi.fn());
vi.mock('@/api/rsvp', () => ({
  useSetRsvp: () => ({ mutateAsync: setRsvpMutate, isPending: false }),
  useRemoveRsvp: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock('@/api/publicRsvp', () => ({
  useUpdatePublicMyRsvp: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useCancelPublicMyRsvp: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

const HOUR = 60 * 60 * 1000;

function makeEvent(overrides: Partial<Event> = {}): Event {
  return makeBaseEvent({ createdById: 'user-host', guests: [], ...overrides });
}

function renderSection(event: Event, deadlineClosed = false) {
  return renderWithProviders(<MyRsvpSection event={event} deadlineClosed={deadlineClosed} />);
}

beforeEach(() => {
  setRsvpMutate.mockReset();
  setRsvpMutate.mockResolvedValue(undefined);
  setAuthed(makeUser({ id: 'user-me' }));
});

describe('MyRsvpSection — open rsvp deadline', () => {
  const deadline = new Date(Date.now() + 48 * HOUR);

  it('shows the rsvp-by date', () => {
    renderSection(makeEvent({ myRsvp: null, rsvpDeadline: deadline }));
    expect(screen.getByText(/^rsvp by /)).toBeInTheDocument();
  });

  it('pops up the confirm-by date after rsvping maybe', async () => {
    renderSection(makeEvent({ myRsvp: null, rsvpDeadline: deadline }));

    fireEvent.click(screen.getByRole('button', { name: 'rsvp' }));
    fireEvent.click(screen.getByRole('button', { name: 'maybe' }));
    fireEvent.click(screen.getByRole('button', { name: 'confirm' }));

    expect(await screen.findByRole('dialog', { name: /^confirm by / })).toBeInTheDocument();
    expect(setRsvpMutate).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpStatus.Maybe }),
    );
  });

  it('skips the pop-up when there is no deadline', async () => {
    renderSection(makeEvent({ myRsvp: null }));

    fireEvent.click(screen.getByRole('button', { name: 'rsvp' }));
    fireEvent.click(screen.getByRole('button', { name: 'maybe' }));
    fireEvent.click(screen.getByRole('button', { name: 'confirm' }));

    await vi.waitFor(() => {
      expect(setRsvpMutate).toHaveBeenCalled();
    });
    expect(screen.queryByRole('dialog', { name: /^confirm by / })).not.toBeInTheDocument();
  });
});

describe('MyRsvpSection — past the rsvp deadline', () => {
  const deadline = new Date(Date.now() - HOUR);

  it('hides the rsvp button and explains why', () => {
    renderSection(makeEvent({ myRsvp: null, rsvpDeadline: deadline }), true);
    expect(screen.queryByRole('button', { name: 'rsvp' })).not.toBeInTheDocument();
    expect(screen.getByText(/new rsvps aren't being taken/)).toBeInTheDocument();
  });

  it('locks a maybe in place', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Maybe, rsvpDeadline: deadline }), true);
    expect(screen.queryByRole('button', { name: /edit rsvp/i })).not.toBeInTheDocument();
    expect(screen.getByText(/rsvps can't be changed anymore/)).toBeInTheDocument();
  });

  it("lets someone going switch to can't go", () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Attending, rsvpDeadline: deadline }), true);

    expect(screen.queryByRole('button', { name: /edit rsvp/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: "i can't go anymore" }));

    expect(setRsvpMutate).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpStatus.CantGo }),
    );
  });

  it('drops the waitlist edit button but keeps leave', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Waitlisted, rsvpDeadline: deadline }), true);
    expect(screen.queryByRole('button', { name: 'edit' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'leave waitlist' })).toBeInTheDocument();
  });
});
