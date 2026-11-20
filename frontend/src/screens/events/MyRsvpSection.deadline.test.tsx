import { fireEvent, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { type Event, RsvpServerStatus, RsvpStatus } from '@/models/event';
import { setAuthed } from '@/test/auth';
import { makeEvent, makeUser } from '@/test/fixtures';
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

function renderSection(event: Event, rsvpsClosed = false) {
  return renderWithProviders(<MyRsvpSection event={event} rsvpsClosed={rsvpsClosed} />);
}

function rsvpMaybe() {
  fireEvent.click(screen.getByRole('button', { name: 'rsvp' }));
  fireEvent.click(screen.getByRole('button', { name: 'maybe' }));
  fireEvent.click(screen.getByRole('button', { name: 'confirm' }));
}

async function expectSavedWithoutPopUp() {
  await vi.waitFor(() => {
    expect(setRsvpMutate).toHaveBeenCalled();
  });
  expect(screen.queryByRole('dialog', { name: /^confirm by / })).not.toBeInTheDocument();
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
    rsvpMaybe();

    expect(await screen.findByRole('dialog', { name: /^confirm by / })).toBeInTheDocument();
    expect(setRsvpMutate).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpStatus.Maybe }),
    );
  });

  it('skips the pop-up when there is no deadline', async () => {
    renderSection(makeEvent({ myRsvp: null }));
    rsvpMaybe();
    await expectSavedWithoutPopUp();
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

  it("lets someone going switch to can't go after confirming", async () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Attending, rsvpDeadline: deadline }), true);

    expect(screen.queryByRole('button', { name: /edit rsvp/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: "i can't go anymore" }));
    const dialog = screen.getByRole('dialog', { name: "can't go anymore?" });
    expect(setRsvpMutate).not.toHaveBeenCalled();
    fireEvent.click(within(dialog).getByRole('button', { name: "i can't go" }));

    await vi.waitFor(() => {
      expect(setRsvpMutate).toHaveBeenCalledWith(
        expect.objectContaining({ status: RsvpStatus.CantGo }),
      );
    });
  });

  it('drops the waitlist edit button but keeps leave', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Waitlisted, rsvpDeadline: deadline }), true);
    expect(screen.queryByRole('button', { name: 'edit' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'leave waitlist' })).toBeInTheDocument();
    expect(screen.getByText(/you can still leave the waitlist/)).toBeInTheDocument();
  });
});

describe('MyRsvpSection — host past the rsvp deadline', () => {
  const deadline = new Date(Date.now() - HOUR);

  it('drops the rsvp-by note', () => {
    renderSection(makeEvent({ myRsvp: null, rsvpDeadline: deadline }));
    expect(screen.queryByText(/rsvp by /)).not.toBeInTheDocument();
  });

  it('skips the confirm-by pop-up after picking maybe', async () => {
    renderSection(makeEvent({ myRsvp: null, rsvpDeadline: deadline }));
    rsvpMaybe();
    await expectSavedWithoutPopUp();
  });
});
