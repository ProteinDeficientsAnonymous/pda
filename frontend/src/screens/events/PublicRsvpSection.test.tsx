import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import {
  canPublicRsvp,
  type Event,
  EventStatus,
  EventType,
  EventVisibility,
  InvitePermission,
} from '@/models/event';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockSubmit = vi.fn();
vi.mock('@/api/publicRsvp', () => ({
  useSubmitPublicRsvp: () => ({ mutateAsync: mockSubmit, isPending: false }),
}));

import { PublicRsvpSection } from './PublicRsvpSection';

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 'ev1',
    title: 'Potluck',
    description: '',
    startDatetime: new Date('2099-06-01T18:00:00Z'),
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

describe('canPublicRsvp', () => {
  it('is true for official + public + rsvpEnabled + active + not-past', () => {
    expect(canPublicRsvp(makeEvent())).toBe(true);
  });
  it('is false for community events', () => {
    expect(canPublicRsvp(makeEvent({ eventType: EventType.Community }))).toBe(false);
  });
  it('is false for members-only visibility', () => {
    expect(canPublicRsvp(makeEvent({ visibility: EventVisibility.MembersOnly }))).toBe(false);
  });
  it('is false when rsvp disabled', () => {
    expect(canPublicRsvp(makeEvent({ rsvpEnabled: false }))).toBe(false);
  });
  it('is false when cancelled', () => {
    expect(canPublicRsvp(makeEvent({ status: EventStatus.Cancelled }))).toBe(false);
  });
  it('is false when past', () => {
    expect(canPublicRsvp(makeEvent({ isPast: true }))).toBe(false);
  });
});

describe('PublicRsvpSection', () => {
  it('renders the form heading initially', () => {
    render(
      <MemoryRouter>
        <PublicRsvpSection event={makeEvent()} />
      </MemoryRouter>,
    );
    expect(screen.getByRole('heading', { name: 'rsvp' })).toBeInTheDocument();
  });

  it('navigates to the event page with the rsvp token on success', async () => {
    mockSubmit.mockResolvedValue({
      event: makeEvent(),
      rsvp: { status: 'attending', has_plus_one: false },
      rsvp_token: 'tok-abc',
    });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <PublicRsvpSection event={makeEvent({ id: 'evt-1' })} />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole('button', { name: "i'm going" }));
    await user.type(screen.getByLabelText(/first name/i), 'Sam');
    await user.type(screen.getByLabelText(/^email/i), 'sam@example.com');
    await user.type(screen.getByLabelText(/phone/i), '4155550123');
    await user.click(screen.getByRole('button', { name: 'rsvp' }));

    expect(mockNavigate).toHaveBeenCalledWith('/events/evt-1?rsvp_token=tok-abc', {
      replace: true,
    });
  });
});
