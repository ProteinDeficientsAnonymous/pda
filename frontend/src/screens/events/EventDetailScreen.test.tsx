import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import { EventStatus, EventType, EventVisibility, InvitePermission } from '@/models/event';
import type { User } from '@/models/user';

vi.mock('@/api/events', () => ({
  useEvent: vi.fn(),
  eventKeys: {
    all: ['events'],
    list: vi.fn(),
    detail: vi.fn(),
  },
}));

// Stub sub-components that make their own mutations/queries
vi.mock('./RsvpSection', () => ({
  RsvpSection: () => <div data-testid="rsvp-section" />,
}));

vi.mock('./InviteDialog', () => ({
  InviteDialog: () => null,
}));

vi.mock('@/utils/datetime', () => ({
  formatEventDateTime: vi.fn().mockReturnValue('Saturday, Jan 1 · 6:00 PM'),
}));

import { useEvent } from '@/api/events';
import EventDetailScreen from './EventDetailScreen';

const mockUseEvent = vi.mocked(useEvent);

const BASE_EVENT: Event = {
  id: 'ev1',
  title: 'Test Event',
  description: 'A test event description',
  startDatetime: new Date('2024-06-01T18:00:00Z'),
  endDatetime: new Date('2024-06-01T20:00:00Z'),
  location: '123 Main St, Brooklyn, NY',
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
  allowPlusOnes: false,
  maxAttendees: null,
  attendingCount: 0,
  waitlistedCount: 0,
  invitedCount: 0,
  datetimeTbd: false,
  hasPoll: false,
  datetimePollSlug: null,
  createdById: 'user1',
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
  invitePermission: InvitePermission.CoHostsOnly,
  pendingCohostInvites: [],
  myPendingCohostInviteId: null,
  eventType: EventType.Community,
  visibility: EventVisibility.Public,
  photoUrl: '',
  isPast: false,
  status: EventStatus.Active,
};

const AUTHED_USER: User = {
  id: 'user-me',
  phoneNumber: '+12125550001',
  displayName: 'Test Member',
  email: 'test@example.com',
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

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderScreen(eventId = 'ev1') {
  return render(
    <QueryClientProvider client={makeQc()}>
      <MemoryRouter initialEntries={[`/events/${eventId}`]}>
        <Routes>
          <Route path="/events/:id" element={<EventDetailScreen />} />
          <Route path="/login" element={<div>login page</div>} />
          <Route path="/join" element={<div>join page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
  vi.clearAllMocks();

  // Default: success with base event
  mockUseEvent.mockReturnValue({
    data: BASE_EVENT,
    isPending: false,
    isError: false,
  } as ReturnType<typeof useEvent>);
});

describe('EventDetailScreen', () => {
  it('renders the event title', () => {
    renderScreen();
    expect(screen.getByRole('heading', { name: /test event/i })).toBeInTheDocument();
  });

  it('shows location for authenticated member', () => {
    useAuthStore.setState({ status: 'authed', user: AUTHED_USER, accessToken: 'tok' });
    renderScreen();

    // LocationSection renders the first segment of the address as a link
    expect(screen.getByRole('link', { name: /123 Main St/i })).toBeInTheDocument();
  });

  it('hides location for unauthenticated guest', () => {
    useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
    renderScreen();

    // Location link should not appear — unauthed users see LoginOrJoinSection instead
    expect(screen.queryByRole('link', { name: /123 Main St/i })).not.toBeInTheDocument();
  });

  it('renders the event description', () => {
    renderScreen();
    expect(screen.getByText(/a test event description/i)).toBeInTheDocument();
  });

  it('shows WhatsApp link for authenticated member', () => {
    useAuthStore.setState({ status: 'authed', user: AUTHED_USER, accessToken: 'tok' });
    renderScreen();

    expect(screen.getByRole('link', { name: /whatsapp group/i })).toBeInTheDocument();
  });

  it('hides WhatsApp link for unauthenticated guest', () => {
    useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
    renderScreen();

    expect(screen.queryByRole('link', { name: /whatsapp group/i })).not.toBeInTheDocument();
  });

  it('shows sign-in and join CTAs for unauthenticated guest', () => {
    useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
    renderScreen();

    expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /request to join/i })).toBeInTheDocument();
  });
});
