import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import { EventStatus, EventType, EventVisibility, InvitePermission } from '@/models/event';
import type { User } from '@/models/user';

vi.mock('@/api/events', () => ({
  useEvent: vi.fn(),
  eventKeys: { all: ['events'], list: vi.fn(), detail: vi.fn() },
}));

vi.mock('@/api/eventStats', () => ({
  useEventStats: vi.fn().mockReturnValue({ data: undefined, isLoading: true, isError: false }),
  useSetAttendance: () => ({ mutate: vi.fn(), isPending: false }),
}));

import { useEvent } from '@/api/events';
import EventAttendanceScreen from './EventAttendanceScreen';

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
  rsvpEnabled: true,
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

function renderScreen() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/events/ev1/attendance']}>
        <Routes>
          <Route path="/events/:id/attendance" element={<EventAttendanceScreen />} />
          <Route path="/events/:id" element={<div>event detail</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(useEvent).mockReturnValue({
    data: BASE_EVENT,
    isPending: false,
    isError: false,
  } as ReturnType<typeof useEvent>);
});

describe('EventAttendanceScreen', () => {
  it('renders the panel for the event creator', () => {
    useAuthStore.setState({ status: 'authed', user: CREATOR, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByRole('heading', { name: /attendance/i })).toBeInTheDocument();
    expect(screen.getByText(BASE_EVENT.title)).toBeInTheDocument();
  });

  it('blocks non-host members with a forbidden notice', () => {
    useAuthStore.setState({ status: 'authed', user: STRANGER, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByText(/only the host or a co-host/i)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /^attendance$/i })).not.toBeInTheDocument();
  });
});
