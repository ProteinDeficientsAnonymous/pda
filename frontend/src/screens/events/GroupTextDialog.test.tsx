import { render, screen, fireEvent } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Event } from '@/models/event';
import { RsvpServerStatus } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

const toastSuccess = vi.fn();
const toastError = vi.fn();
const toastInfo = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    success: (m: string) => {
      toastSuccess(m);
    },
    error: (m: string) => {
      toastError(m);
    },
    info: (m: string) => {
      toastInfo(m);
    },
  },
}));

import { GroupTextDialog } from './GroupTextDialog';

function guest(overrides: Partial<Event['guests'][number]>): Event['guests'][number] {
  return {
    userId: 'u',
    name: 'someone',
    status: RsvpServerStatus.Attending,
    phone: null,
    photoUrl: '',
    hasPlusOne: false,
    attendance: 'unknown',
    ...overrides,
  };
}

// alice = going, carol = maybe, bob = cant_go.
const EVENT = makeEvent({
  guests: [
    guest({ userId: 'a', phone: '+15551112222', status: RsvpServerStatus.Attending }),
    guest({ userId: 'c', phone: '+15559990000', status: RsvpServerStatus.Maybe }),
    guest({ userId: 'b', phone: '+15553334444', status: RsvpServerStatus.CantGo }),
  ],
});

const noop = () => {};
const originalUserAgent = navigator.userAgent;

beforeEach(() => {
  toastSuccess.mockClear();
  toastError.mockClear();
  toastInfo.mockClear();
  // Pin an Apple UA so buildSmsUri emits the /open?addresses= form.
  Object.defineProperty(navigator, 'userAgent', {
    value: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    configurable: true,
  });
});

afterEach(() => {
  Object.defineProperty(navigator, 'userAgent', { value: originalUserAgent, configurable: true });
  vi.restoreAllMocks();
});

describe('GroupTextDialog', () => {
  it('defaults to going + maybe selected', () => {
    render(<GroupTextDialog event={EVENT} open onClose={noop} />);
    const pressed = screen.getAllByRole('button', { pressed: true }).map((el) => el.textContent);
    expect(pressed).toEqual(['going1', 'maybe1']);
    expect(screen.getAllByRole('button', { pressed: false }).map((el) => el.textContent)).toContain(
      "can't go1",
    );
  });

  it('renders an sms: group-draft link (Apple /open?addresses= form) for the selected groups', () => {
    render(<GroupTextDialog event={EVENT} open onClose={noop} />);
    const link = screen.getByRole('link', { name: /text them/i });
    expect(link).toHaveAttribute('href', 'sms:/open?addresses=+15551112222,+15559990000');
  });

  it('updates the sms: link when a group is toggled', () => {
    render(<GroupTextDialog event={EVENT} open onClose={noop} />);
    fireEvent.click(screen.getByRole('button', { name: /^maybe/i }));
    fireEvent.click(screen.getByRole('button', { name: /can't go/i }));
    const link = screen.getByRole('link', { name: /text them/i });
    expect(link).toHaveAttribute('href', 'sms:/open?addresses=+15551112222,+15553334444');
  });

  it('closes and surfaces skipped count when texting', () => {
    const onClose = vi.fn();
    const event = makeEvent({
      guests: [
        guest({ userId: 'a', phone: '+15551112222', status: RsvpServerStatus.Attending }),
        guest({ userId: 'x', phone: null, status: RsvpServerStatus.Attending }),
      ],
    });
    render(<GroupTextDialog event={event} open onClose={onClose} />);
    fireEvent.click(screen.getByRole('link', { name: /text them/i }));
    expect(toastInfo).toHaveBeenCalledWith("1 person has no number and weren't included");
    expect(onClose).toHaveBeenCalled();
  });

  it('copies numbers via the secondary copy action and closes', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
    const onClose = vi.fn();

    render(<GroupTextDialog event={EVENT} open onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: /copy numbers instead/i }));
    await vi.waitFor(() => {
      expect(writeText).toHaveBeenCalledWith('+15551112222, +15559990000');
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('does not offer a group with no textable people', () => {
    const event = makeEvent({
      guests: [guest({ userId: 'a', phone: '+15551112222', status: RsvpServerStatus.Attending })],
    });
    render(<GroupTextDialog event={event} open onClose={noop} />);
    expect(screen.queryByRole('button', { name: /^maybe/i })).toBeNull();
    expect(screen.queryByRole('button', { name: /invited/i })).toBeNull();
  });

  it('offers the invited group when invited phones are present', () => {
    const event = makeEvent({
      guests: [guest({ userId: 'a', phone: '+15551112222', status: RsvpServerStatus.Attending })],
      invitedUserPhones: ['+15558887777'],
    });
    render(<GroupTextDialog event={event} open onClose={noop} />);
    expect(screen.getByRole('button', { name: /invited/i })).toBeInTheDocument();
  });
});
