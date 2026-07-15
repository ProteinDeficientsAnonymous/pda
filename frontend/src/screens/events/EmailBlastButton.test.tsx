import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { Event, EventGuest } from '@/models/event';
import { EventStatus, EventType, EventVisibility, InvitePermission } from '@/models/event';

vi.mock('./EmailBlastDialog', () => ({
  EmailBlastDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="email-blast-dialog" /> : null,
}));

import { EmailBlastButton } from './EmailBlastButton';

function guest(status: string): EventGuest {
  return {
    userId: 'g1',
    name: 'Guest',
    status,
    phone: null,
    photoUrl: '',
    hasPlusOne: false,
    attendance: 'unknown',
  };
}

function makeEvent(overrides: Partial<Event> = {}): Event {
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
    guests: [guest('attending')],
    myRsvp: null,
    viewerUserId: null,
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
    photoUpdatedAt: null,
    tags: [],
    isPast: false,
    status: EventStatus.Active,
    ...overrides,
  };
}

describe('EmailBlastButton', () => {
  it('renders the email-blast button when the event has guests', () => {
    render(<EmailBlastButton event={makeEvent()} />);
    expect(screen.getByRole('button', { name: /email blast/i })).toBeInTheDocument();
  });

  it('renders nothing when no one has rsvpd', () => {
    render(<EmailBlastButton event={makeEvent({ guests: [] })} />);
    expect(screen.queryByRole('button', { name: /email blast/i })).not.toBeInTheDocument();
  });

  it('renders nothing for a draft event', () => {
    render(<EmailBlastButton event={makeEvent({ status: EventStatus.Draft })} />);
    expect(screen.queryByRole('button', { name: /email blast/i })).not.toBeInTheDocument();
  });

  it('opens the dialog when clicked', async () => {
    render(<EmailBlastButton event={makeEvent()} />);
    expect(screen.queryByTestId('email-blast-dialog')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /email blast/i }));
    expect(screen.getByTestId('email-blast-dialog')).toBeInTheDocument();
  });
});
