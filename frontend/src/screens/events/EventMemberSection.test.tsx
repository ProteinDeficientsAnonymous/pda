import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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

const ACCEPTED_COHOST_EVENT: Event = {
  ...BASE_EVENT,
  coHostIds: ['user-bob'],
  coHostNames: ['Bob'],
  coHostPhotoUrls: [''],
  coHostInviteIds: ['inv-accepted-1'],
};

const COHOST_BOB: User = { ...CREATOR, id: 'user-bob', displayName: 'Bob' };

describe('EventMemberSection — accepted host row', () => {
  it('renders × on accepted co-host chip for host viewer', () => {
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderSection(ACCEPTED_COHOST_EVENT);
    expect(screen.getByRole('button', { name: /remove bob as co-host/i })).toBeInTheDocument();
  });

  it('does NOT render × on creator chip', () => {
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderSection(ACCEPTED_COHOST_EVENT);
    // Creator chip is "Alice" — no × should appear next to it.
    expect(
      screen.queryByRole('button', { name: /remove alice as co-host/i }),
    ).not.toBeInTheDocument();
  });

  it('does NOT render × on accepted co-host chip for outsider', () => {
    useAuthStore.setState({ status: 'authed', user: STRANGER, accessToken: 'tok' });
    renderSection(ACCEPTED_COHOST_EVENT);
    expect(
      screen.queryByRole('button', { name: /remove bob as co-host/i }),
    ).not.toBeInTheDocument();
  });

  it('host removal fires the mutation immediately (no confirm)', () => {
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderSection(ACCEPTED_COHOST_EVENT);
    fireEvent.click(screen.getByRole('button', { name: /remove bob as co-host/i }));
    expect(rescindMutate).toHaveBeenCalledWith(
      { eventId: 'ev1', inviteId: 'inv-accepted-1' },
      expect.any(Object),
    );
  });

  it('shows step-down × when viewer is the cohost themselves', () => {
    useAuthStore.setState({ status: 'authed', user: COHOST_BOB, accessToken: 'tok' });
    renderSection(ACCEPTED_COHOST_EVENT);
    expect(screen.getByRole('button', { name: /step down as co-host/i })).toBeInTheDocument();
  });

  it('self-step-down shows confirm dialog and does NOT fire mutation until confirmed', async () => {
    useAuthStore.setState({ status: 'authed', user: COHOST_BOB, accessToken: 'tok' });
    renderSection(ACCEPTED_COHOST_EVENT);
    fireEvent.click(screen.getByRole('button', { name: /step down as co-host/i }));
    // Dialog appears; mutation has NOT fired yet.
    expect(rescindMutate).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /^step down$/i })).toBeInTheDocument();
    // Confirm.
    fireEvent.click(screen.getByRole('button', { name: /^step down$/i }));
    await waitFor(() => {
      expect(rescindMutate).toHaveBeenCalledWith(
        { eventId: 'ev1', inviteId: 'inv-accepted-1' },
        expect.any(Object),
      );
    });
  });

  it('cancelling the step-down confirm does NOT fire the mutation', async () => {
    useAuthStore.setState({ status: 'authed', user: COHOST_BOB, accessToken: 'tok' });
    renderSection(ACCEPTED_COHOST_EVENT);
    fireEvent.click(screen.getByRole('button', { name: /step down as co-host/i }));
    fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }));
    // Give the promise chain a tick to resolve before asserting "didn't fire".
    await Promise.resolve();
    expect(rescindMutate).not.toHaveBeenCalled();
  });
});

describe('EventMemberSection — past event gates (#385)', () => {
  it('hides the + button on past events', () => {
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderSection({ ...BASE_EVENT, isPast: true });
    expect(screen.queryByRole('button', { name: /add co-host/i })).not.toBeInTheDocument();
  });

  it('shows the + button on non-past events for host viewer', () => {
    // Sanity check that the gate is doing the right thing — should still render
    // when the event is in the future.
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderSection(BASE_EVENT);
    expect(screen.getByRole('button', { name: /add co-host/i })).toBeInTheDocument();
  });

  it('still allows × on accepted host chips for past events (housekeeping)', () => {
    // Removing an accepted cohost must keep working post-event — backend allows
    // it, so the FE should too.
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderSection({ ...ACCEPTED_COHOST_EVENT, isPast: true });
    expect(screen.getByRole('button', { name: /remove bob as co-host/i })).toBeInTheDocument();
  });
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
