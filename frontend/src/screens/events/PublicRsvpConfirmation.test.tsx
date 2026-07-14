import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import type { PublicRsvpOut } from '@/api/publicRsvp';
import {
  type Event,
  EventStatus,
  EventType,
  EventVisibility,
  InvitePermission,
} from '@/models/event';

import { PublicRsvpConfirmation } from './PublicRsvpConfirmation';

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 'ev1',
    title: 'Community Potluck',
    description: '',
    startDatetime: new Date('2099-06-01T18:00:00Z'),
    endDatetime: null,
    location: '123 Main St',
    latitude: null,
    longitude: null,
    whatsappLink: 'https://chat.whatsapp.com/abc',
    partifulLink: '',
    otherLink: '',
    venmoLink: '',
    cashappLink: '',
    zelleInfo: '',
    price: '',
    rsvpEnabled: true,
    allowPlusOnes: true,
    maxAttendees: null,
    attendingCount: 0,
    waitlistedCount: 0,
    invitedCount: 0,
    datetimeTbd: false,
    hasPoll: false,
    datetimePollSlug: null,
    createdById: null,
    createdByName: null,
    createdByPhotoUrl: '',
    coHostIds: [],
    coHostNames: [],
    coHostPhotoUrls: [],
    coHostInviteIds: [],
    guests: [],
    myRsvp: null,
    surveySlugs: [],
    invitedUserIds: [],
    invitedUserNames: [],
    invitedUserPhotoUrls: [],
    invitePermission: InvitePermission.AllMembers,
    pendingCohostInvites: [],
    myPendingCohostInviteId: null,
    eventType: EventType.Official,
    visibility: EventVisibility.Public,
    photoUrl: '',
    photoUpdatedAt: null,
    tags: [],
    isPast: false,
    status: EventStatus.Active,
    ...overrides,
  };
}

function out(status: string): PublicRsvpOut {
  return { event: { id: 'ev1' } as never, rsvp: { status, has_plus_one: false } };
}

function renderCard(status: string, event = makeEvent()) {
  return render(
    <MemoryRouter>
      <PublicRsvpConfirmation event={event} result={out(status)} />
    </MemoryRouter>,
  );
}

describe('PublicRsvpConfirmation', () => {
  it('shows the attending heading and event info', () => {
    renderCard('attending');
    expect(screen.getByText("you're in! 🌱")).toBeInTheDocument();
    expect(screen.getByText('Community Potluck')).toBeInTheDocument();
    expect(screen.getByText('123 Main St')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /whatsapp/i })).toBeInTheDocument();
  });

  it('shows the waitlist heading', () => {
    renderCard('waitlisted');
    expect(screen.getByText("you're on the waitlist")).toBeInTheDocument();
  });

  it('shows the emailed-link line and join CTA', () => {
    renderCard('attending');
    expect(
      screen.getByText('we just emailed you a link to manage your rsvp — check your inbox'),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'request to join' })).toHaveAttribute('href', '/join');
  });
});
