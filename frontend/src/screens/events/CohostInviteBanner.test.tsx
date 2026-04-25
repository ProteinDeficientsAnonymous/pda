import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Event } from '@/models/event';
import { EventStatus, EventType, EventVisibility, InvitePermission } from '@/models/event';

const acceptMutate = vi.fn();
const declineMutate = vi.fn();

vi.mock('@/api/cohostInvites', () => ({
  useAcceptCohostInvite: () => ({ mutate: acceptMutate, isPending: false }),
  useDeclineCohostInvite: () => ({ mutate: declineMutate, isPending: false }),
  useRescindCohostInvite: () => ({ mutate: vi.fn(), isPending: false }),
}));

import { CohostInviteBanner } from './CohostInviteBanner';

const BASE_EVENT: Event = {
  id: 'ev1',
  title: 'Spring Potluck',
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
  rsvpEnabled: false,
  allowPlusOnes: false,
  maxAttendees: null,
  attendingCount: 0,
  waitlistedCount: 0,
  invitedCount: 0,
  datetimeTbd: false,
  hasPoll: false,
  datetimePollSlug: null,
  createdById: 'user-creator',
  createdByName: 'Alice',
  createdByPhotoUrl: '',
  coHostIds: [],
  coHostNames: [],
  coHostPhotoUrls: [],
  guests: [],
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

function renderBanner(event: Event) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CohostInviteBanner event={event} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  acceptMutate.mockReset();
  declineMutate.mockReset();
});

describe('CohostInviteBanner', () => {
  it('renders nothing when there is no pending invite for the viewer', () => {
    const { container } = renderBanner(BASE_EVENT);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when the event is past, even with a pending invite', () => {
    const { container } = renderBanner({
      ...BASE_EVENT,
      myPendingCohostInviteId: 'inv1',
      isPast: true,
    });
    expect(container).toBeEmptyDOMElement();
  });

  it('renders the inviter name and accept/decline buttons when there is a pending invite', () => {
    renderBanner({ ...BASE_EVENT, myPendingCohostInviteId: 'inv1' });
    expect(screen.getByText(/alice invited you to co-host/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /accept/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /decline/i })).toBeInTheDocument();
  });

  it('falls back to "someone" when the creator name is missing', () => {
    renderBanner({
      ...BASE_EVENT,
      myPendingCohostInviteId: 'inv1',
      createdByName: null,
    });
    expect(screen.getByText(/someone invited you/i)).toBeInTheDocument();
  });

  it('fires the accept mutation with the invite id when accept is clicked', () => {
    renderBanner({ ...BASE_EVENT, myPendingCohostInviteId: 'inv1' });
    fireEvent.click(screen.getByRole('button', { name: /accept/i }));
    expect(acceptMutate).toHaveBeenCalledWith(
      { eventId: 'ev1', inviteId: 'inv1' },
      expect.any(Object),
    );
  });

  it('fires the decline mutation when decline is clicked', () => {
    renderBanner({ ...BASE_EVENT, myPendingCohostInviteId: 'inv1' });
    fireEvent.click(screen.getByRole('button', { name: /decline/i }));
    expect(declineMutate).toHaveBeenCalledWith(
      { eventId: 'ev1', inviteId: 'inv1' },
      expect.any(Object),
    );
  });
});
