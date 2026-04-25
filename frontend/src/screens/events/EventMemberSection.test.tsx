import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import { EventStatus, EventType, EventVisibility, InvitePermission } from '@/models/event';
import type { User } from '@/models/user';

const rescindMutate = vi.fn();

vi.mock('@/api/cohostInvites', () => ({
  useAcceptCohostInvite: () => ({ mutate: vi.fn(), isPending: false }),
  useDeclineCohostInvite: () => ({ mutate: vi.fn(), isPending: false }),
  useRescindCohostInvite: () => ({ mutate: rescindMutate, isPending: false }),
}));

// Stub heavy sub-sections so we focus on the host row.
vi.mock('./RsvpSection', () => ({ RsvpSection: () => <div data-testid="rsvp-section" /> }));
vi.mock('./RsvpGuestList', () => ({ InvitedList: () => null }));
vi.mock('./EventAdminActions', () => ({ EventAdminActions: () => null }));
vi.mock('./EventAttendancePanel', () => ({ EventAttendancePanel: () => null }));
vi.mock('./EventFlagDialog', () => ({ EventFlagDialog: () => null }));
vi.mock('./InviteDialog', () => ({ InviteDialog: () => null }));
vi.mock('./AddCoHostDialog', () => ({ AddCoHostDialog: () => null }));

import { EventMemberSection } from './EventMemberSection';

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

const CREATOR: User = {
  id: 'user-creator',
  phoneNumber: '+12125550001',
  displayName: 'Alice',
  email: '',
  bio: '',
  isSuperuser: false,
  isStaff: false,
  needsOnboarding: false,
  showPhone: false,
  showEmail: false,
  weekStart: 'sunday',
  calendarFeedScope: 'all',
  profilePhotoUrl: '',
  photoUpdatedAt: null,
  roles: [],
};

const STRANGER: User = { ...CREATOR, id: 'user-stranger', displayName: 'Stranger' };

function renderSection(event: Event) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <EventMemberSection event={event} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  rescindMutate.mockReset();
});

describe('EventMemberSection — pending host row', () => {
  it('renders pending invitee chips for a host viewer', () => {
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderSection({
      ...BASE_EVENT,
      pendingCohostInvites: [
        {
          id: 'inv1',
          userId: 'user-bob',
          userName: 'Bob',
          userPhotoUrl: '',
          invitedAt: new Date(),
        },
      ],
    });

    expect(screen.getByLabelText(/bob \(pending\)/i)).toBeInTheDocument();
    expect(screen.getByText(/pending/i)).toBeInTheDocument();
  });

  it('shows the rescind button only when the viewer is a host', () => {
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderSection({
      ...BASE_EVENT,
      pendingCohostInvites: [
        {
          id: 'inv1',
          userId: 'user-bob',
          userName: 'Bob',
          userPhotoUrl: '',
          invitedAt: new Date(),
        },
      ],
    });

    expect(screen.getByRole('button', { name: /rescind invite to bob/i })).toBeInTheDocument();
  });

  it('does not render pending chips when the backend hasnt returned any (non-host viewer)', () => {
    // Backend gates the list — a non-host gets [].
    useAuthStore.setState({ status: 'authed', user: STRANGER, accessToken: 'tok' });
    renderSection({ ...BASE_EVENT, pendingCohostInvites: [] });

    expect(screen.queryByText(/pending/i)).not.toBeInTheDocument();
  });

  it('fires the rescind mutation when × is clicked', () => {
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderSection({
      ...BASE_EVENT,
      pendingCohostInvites: [
        {
          id: 'inv1',
          userId: 'user-bob',
          userName: 'Bob',
          userPhotoUrl: '',
          invitedAt: new Date(),
        },
      ],
    });

    fireEvent.click(screen.getByRole('button', { name: /rescind invite to bob/i }));
    expect(rescindMutate).toHaveBeenCalledWith(
      { eventId: 'ev1', inviteId: 'inv1' },
      expect.any(Object),
    );
  });
});
