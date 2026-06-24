import { render, screen, fireEvent } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Event } from '@/models/event';
import type * as GroupTextModule from '@/utils/groupText';
import { AttendanceStatus, RsvpServerStatus } from '@/models/event';
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

const isSmsSupported = vi.fn<() => boolean>();
vi.mock('@/utils/groupText', async (importOriginal) => {
  const actual = await importOriginal<typeof GroupTextModule>();
  return { ...actual, isSmsSupported: () => isSmsSupported() };
});

import { GroupTextButton } from './GroupTextButton';

const BASE_EVENT = makeEvent();

function withGuests(guests: Event['guests']): Event {
  return makeEvent({ guests });
}

beforeEach(() => {
  toastSuccess.mockClear();
  toastError.mockClear();
  toastInfo.mockClear();
  isSmsSupported.mockReset();
  isSmsSupported.mockReturnValue(true);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('GroupTextButton', () => {
  it('opens an sms: group thread with all eligible numbers', () => {
    const hrefSetter = vi.fn();
    const originalLocation = window.location;
    Object.defineProperty(window, 'location', {
      value: {
        set href(v: string) {
          hrefSetter(v);
        },
      },
      configurable: true,
    });

    try {
      render(<GroupTextButton event={BASE_EVENT} />);
      fireEvent.click(screen.getByRole('button', { name: /text attendees/i }));
      expect(hrefSetter).toHaveBeenCalledWith('sms:+15551112222,+15553334444');
    } finally {
      Object.defineProperty(window, 'location', {
        value: originalLocation,
        configurable: true,
      });
    }
  });

  it('surfaces the skipped-no-number count in a toast', () => {
    const originalLocation = window.location;
    Object.defineProperty(window, 'location', {
      value: { set href(_v: string) {} },
      configurable: true,
    });

    const event = withGuests([
      ...BASE_EVENT.guests,
      {
        userId: 'c',
        name: 'carol',
        status: RsvpServerStatus.Maybe,
        phone: null,
        photoUrl: '',
        hasPlusOne: false,
        attendance: AttendanceStatus.Unknown,
      },
    ]);
    try {
      render(<GroupTextButton event={event} />);
      fireEvent.click(screen.getByRole('button', { name: /text attendees/i }));
      expect(toastInfo).toHaveBeenCalledWith("1 attendee has no number and weren't included");
    } finally {
      Object.defineProperty(window, 'location', {
        value: originalLocation,
        configurable: true,
      });
    }
  });
});
