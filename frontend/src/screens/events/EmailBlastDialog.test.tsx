import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Event, EventGuest } from '@/models/event';
import { makeEvent as makeEventFixture } from '@/test/fixtures';

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
    isMember: true,
  };
}

function makeEvent(guests: EventGuest[]): Event {
  return makeEventFixture({
    guests,
    attendingCount: guests.filter((g) => g.status === 'attending').length,
  });
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

// Audience chips are labelled "<group> <count>" (e.g. "going 1").
function chip(label: string): HTMLElement {
  return screen.getByRole('button', { name: new RegExp(`^${label}\\s*\\d+$`, 'i') });
}

beforeEach(() => {
  mutateAsyncMock.mockReset();
  toastSuccessMock.mockReset();
  toastErrorMock.mockReset();
});

describe('EmailBlastDialog', () => {
  it('previews the recipient count with every audience selected by default', () => {
    renderDialog(makeEvent(THREE_GUESTS));
    expect(screen.getByText(/emailing 3 attendees/i)).toBeInTheDocument();
  });

  it('updates the recipient count when narrowing the audience to going only', async () => {
    renderDialog(makeEvent(THREE_GUESTS));
    await userEvent.click(chip('maybe'));
    await userEvent.click(chip("can't go"));
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
        audience: ['attending', 'maybe', 'cant_go'],
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
    await userEvent.click(chip('maybe'));
    await userEvent.click(chip("can't go"));
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
    await userEvent.click(chip('going'));
    await userEvent.click(chip('maybe'));
    await userEvent.click(chip("can't go"));
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
    await userEvent.click(chip('going'));
    await userEvent.click(chip('maybe'));
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
