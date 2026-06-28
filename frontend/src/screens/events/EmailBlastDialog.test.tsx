import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Event, EventGuest } from '@/models/event';
import { EventStatus, EventType, EventVisibility, InvitePermission } from '@/models/event';

const mutateAsyncMock = vi.fn();
const toastSuccessMock = vi.fn();
const toastErrorMock = vi.fn();

vi.mock('@/api/eventBlast', () => ({
  useEmailBlast: () => ({ mutateAsync: mutateAsyncMock, isPending: false }),
}));

vi.mock('sonner', () => ({
  toast: {
    success: (m: string) => {
      toastSuccessMock(m);
    },
    error: (m: string) => {
      toastErrorMock(m);
    },
  },
}));

import { EmailBlastDialog } from './EmailBlastDialog';

function guest(status: string, i: number): EventGuest {
  return {
    userId: `u${String(i)}`,
    name: `Guest ${String(i)}`,
    status,
    phone: null,
    photoUrl: '',
    hasPlusOne: false,
    attendance: 'unknown',
  };
}

function makeEvent(guests: EventGuest[]): Event {
  return {
    id: 'ev1',
    title: 'Potluck',
    description: '',
    startDatetime: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
    endDatetime: null,
    location: '',
    latitude: null,
    longitude: null,
    whatsappLink: '',
    partifulLink: '',
    otherLink: '',
    venmoLink: '',
    cashappLink: '',
    zelleInfo: '',
    price: '',
    rsvpEnabled: true,
    allowPlusOnes: false,
    maxAttendees: null,
    attendingCount: guests.filter((g) => g.status === 'attending').length,
    waitlistedCount: 0,
    invitedCount: 0,
    datetimeTbd: false,
    hasPoll: false,
    datetimePollSlug: null,
    createdById: 'creator',
    createdByName: 'Creator',
    createdByPhotoUrl: '',
    coHostIds: [],
    coHostNames: [],
    coHostPhotoUrls: [],
    coHostInviteIds: [],
    guests,
    myRsvp: null,
    surveySlugs: [],
    invitedUserIds: [],
    invitedUserNames: [],
    invitedUserPhotoUrls: [],
    invitePermission: InvitePermission.CoHostsOnly,
    pendingCohostInvites: [],
    myPendingCohostInviteId: null,
    eventType: EventType.Community,
    visibility: EventVisibility.Public,
    photoUrl: '',
    isPast: false,
    status: EventStatus.Active,
  };
}

function renderDialog(event: Event) {
  const onClose = vi.fn();
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const utils = render(
    <QueryClientProvider client={qc}>
      <EmailBlastDialog event={event} open onClose={onClose} />
    </QueryClientProvider>,
  );
  return { ...utils, onClose };
}

const THREE_GUESTS = [guest('attending', 1), guest('maybe', 2), guest('cant_go', 3)];

beforeEach(() => {
  mutateAsyncMock.mockReset();
  toastSuccessMock.mockReset();
  toastErrorMock.mockReset();
});

describe('EmailBlastDialog', () => {
  it('previews the recipient count for the default everyone audience', () => {
    renderDialog(makeEvent(THREE_GUESTS));
    expect(screen.getByText(/emailing 3 attendees/i)).toBeInTheDocument();
  });

  it('updates the recipient count when narrowing the audience to going only', async () => {
    renderDialog(makeEvent(THREE_GUESTS));
    await userEvent.selectOptions(screen.getByLabelText('send to'), 'going');
    expect(screen.getByText(/emailing 1 attendee\b/i)).toBeInTheDocument();
  });

  it('requires a subject before moving to confirm', async () => {
    renderDialog(makeEvent(THREE_GUESTS));
    await userEvent.type(screen.getByLabelText('message'), 'hello');
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/add a subject/i);
    expect(mutateAsyncMock).not.toHaveBeenCalled();
  });

  it('requires a message before moving to confirm', async () => {
    renderDialog(makeEvent(THREE_GUESTS));
    await userEvent.type(screen.getByLabelText('subject'), 'hi');
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/add a message/i);
    expect(mutateAsyncMock).not.toHaveBeenCalled();
  });

  it('requires a confirmation step before sending', async () => {
    mutateAsyncMock.mockResolvedValue({
      sent_count: 3,
      skipped_no_email_count: 0,
      failed_count: 0,
    });
    renderDialog(makeEvent(THREE_GUESTS));
    await userEvent.type(screen.getByLabelText('subject'), 'schedule update');
    await userEvent.type(screen.getByLabelText('message'), 'we moved to 6pm');
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    expect(mutateAsyncMock).not.toHaveBeenCalled();
    expect(screen.getByText(/can't be undone/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /^send$/i }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith({
        subject: 'schedule update',
        message: 'we moved to 6pm',
      });
    });
  });

  it('sends the chosen audience statuses when narrowed', async () => {
    mutateAsyncMock.mockResolvedValue({
      sent_count: 1,
      skipped_no_email_count: 0,
      failed_count: 0,
    });
    renderDialog(makeEvent(THREE_GUESTS));
    await userEvent.type(screen.getByLabelText('subject'), 'hi');
    await userEvent.type(screen.getByLabelText('message'), 'going folks only');
    await userEvent.selectOptions(screen.getByLabelText('send to'), 'going');
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    await userEvent.click(screen.getByRole('button', { name: /^send$/i }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith({
        subject: 'hi',
        message: 'going folks only',
        audience: ['attending'],
      });
    });
  });

  it('treats waitlisted as its own audience separate from going', async () => {
    mutateAsyncMock.mockResolvedValue({
      sent_count: 1,
      skipped_no_email_count: 0,
      failed_count: 0,
    });
    renderDialog(makeEvent([...THREE_GUESTS, guest('waitlisted', 4)]));
    await userEvent.type(screen.getByLabelText('subject'), 'hi');
    await userEvent.type(screen.getByLabelText('message'), 'waitlist only');
    await userEvent.selectOptions(screen.getByLabelText('send to'), 'waitlisted');
    expect(screen.getByText(/emailing 1 attendee\b/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    await userEvent.click(screen.getByRole('button', { name: /^send$/i }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith({
        subject: 'hi',
        message: 'waitlist only',
        audience: ['waitlisted'],
      });
    });
  });

  it("targets the can't-go audience", async () => {
    mutateAsyncMock.mockResolvedValue({
      sent_count: 1,
      skipped_no_email_count: 0,
      failed_count: 0,
    });
    renderDialog(makeEvent(THREE_GUESTS));
    await userEvent.type(screen.getByLabelText('subject'), 'hi');
    await userEvent.type(screen.getByLabelText('message'), 'sorry you missed it');
    await userEvent.selectOptions(screen.getByLabelText('send to'), 'cant_go');
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    await userEvent.click(screen.getByRole('button', { name: /^send$/i }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith({
        subject: 'hi',
        message: 'sorry you missed it',
        audience: ['cant_go'],
      });
    });
  });

  it('shows a success toast with sent and skipped counts', async () => {
    mutateAsyncMock.mockResolvedValue({
      sent_count: 2,
      skipped_no_email_count: 1,
      failed_count: 0,
    });
    const { onClose } = renderDialog(makeEvent(THREE_GUESTS));
    await userEvent.type(screen.getByLabelText('subject'), 'hi');
    await userEvent.type(screen.getByLabelText('message'), 'body');
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    await userEvent.click(screen.getByRole('button', { name: /^send$/i }));
    await waitFor(() => {
      expect(toastSuccessMock).toHaveBeenCalledWith(expect.stringContaining('sent to 2 attendees'));
    });
    expect(toastSuccessMock).toHaveBeenCalledWith(expect.stringContaining('1 skipped (no email)'));
    expect(onClose).toHaveBeenCalled();
  });
});
