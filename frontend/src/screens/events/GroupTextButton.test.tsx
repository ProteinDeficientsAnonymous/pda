import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Event } from '@/models/event';
import type * as GroupTextModule from '@/utils/groupText';
import {
  AttendanceStatus,
  EventStatus,
  EventType,
  EventVisibility,
  InvitePermission,
  RsvpServerStatus,
} from '@/models/event';

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

const BASE_EVENT: Event = {
  id: 'ev1',
  title: 'Test Event',
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
  attendingCount: 1,
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
  guests: [
    {
      userId: 'a',
      name: 'alice',
      status: RsvpServerStatus.Attending,
      phone: '+15551112222',
      photoUrl: '',
      hasPlusOne: false,
      attendance: AttendanceStatus.Unknown,
    },
    {
      userId: 'b',
      name: 'bob',
      status: RsvpServerStatus.CantGo,
      phone: '+15553334444',
      photoUrl: '',
      hasPlusOne: false,
      attendance: AttendanceStatus.Unknown,
    },
  ],
  myRsvp: null,
  surveySlugs: [],
  invitedUserIds: [],
  invitedUserNames: [],
  invitedUserPhotoUrls: [],
  invitePermission: InvitePermission.AllMembers,
  pendingCohostInvites: [],
  myPendingCohostInviteId: null,
  eventType: EventType.Community,
  visibility: EventVisibility.Public,
  photoUrl: '',
  isPast: false,
  status: EventStatus.Active,
};

function withGuests(guests: Event['guests']): Event {
  return { ...BASE_EVENT, guests };
}

beforeEach(() => {
  toastSuccess.mockClear();
  toastError.mockClear();
  toastInfo.mockClear();
  isSmsSupported.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('GroupTextButton', () => {
  it('opens an sms: group thread with all eligible numbers on mobile', () => {
    isSmsSupported.mockReturnValue(true);
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

  it('falls back to copying the list on desktop and toasts', async () => {
    isSmsSupported.mockReturnValue(false);
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });

    render(<GroupTextButton event={BASE_EVENT} />);
    fireEvent.click(screen.getByRole('button', { name: /copy attendee numbers/i }));

    expect(writeText).toHaveBeenCalledWith('+15551112222, +15553334444');
    await waitFor(() => {
      expect(toastSuccess).toHaveBeenCalledWith('copied 2 numbers');
    });
  });

  it('surfaces the skipped-no-number count in the copy toast', async () => {
    isSmsSupported.mockReturnValue(false);
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
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
    render(<GroupTextButton event={event} />);
    fireEvent.click(screen.getByRole('button', { name: /copy attendee numbers/i }));

    await waitFor(() => {
      expect(toastSuccess).toHaveBeenCalledWith(
        "copied 2 numbers — 1 attendee has no number and weren't included",
      );
    });
  });

  it('surfaces the skipped-no-number count on the mobile sms path too', () => {
    isSmsSupported.mockReturnValue(true);
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

  it('disables the action when no attendee has a phone number', () => {
    isSmsSupported.mockReturnValue(false);
    const event = withGuests([
      {
        userId: 'a',
        name: 'alice',
        status: RsvpServerStatus.Attending,
        phone: null,
        photoUrl: '',
        hasPlusOne: false,
        attendance: AttendanceStatus.Unknown,
      },
    ]);
    render(<GroupTextButton event={event} />);

    expect(screen.getByRole('button', { name: /copy attendee numbers/i })).toBeDisabled();
  });
});
