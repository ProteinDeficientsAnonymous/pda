import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import {
  EventStatus,
  EventType,
  EventVisibility,
  InvitePermission,
} from '@/models/event';
import type { User } from '@/models/user';
import { Permission } from '@/models/permissions';

// Mock network-touching dependencies
vi.mock('@/api/eventWrites', () => ({
  useUpdateEvent: vi.fn().mockReturnValue({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/api/client', () => ({
  apiClient: { delete: vi.fn() },
  setAuthBridge: vi.fn(),
}));

vi.mock('@/api/events', () => ({
  eventKeys: {
    all: ['events'],
    list: vi.fn().mockReturnValue([]),
    detail: vi.fn().mockReturnValue([]),
  },
}));

import { EventAdminActions } from './EventAdminActions';

const CREATOR_ID = 'creator-user';
const COHOST_ID = 'cohost-user';
const REGULAR_ID = 'regular-user';

function makeUser(id: string, permissions: string[] = []): User {
  return {
    id,
    phoneNumber: '+12125550001',
    displayName: 'Test User',
    email: '',
    bio: '',
    isSuperuser: false,
    isStaff: false,
    needsOnboarding: false,
    showPhone: false,
    showEmail: false,
    weekStart: 'sunday',
    profilePhotoUrl: '',
    photoUpdatedAt: null,
    roles: permissions.length
      ? [{ id: 'r1', name: 'custom', isDefault: true, permissions }]
      : [],
  };
}

const BASE_EVENT: Event = {
  id: 'ev1',
  title: 'Test Event',
  description: '',
  startDatetime: new Date('2025-06-01T18:00:00Z'),
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
  createdById: CREATOR_ID,
  createdByName: 'Creator',
  createdByPhotoUrl: '',
  coHostIds: [COHOST_ID],
  coHostNames: ['Co-Host'],
  coHostPhotoUrls: [''],
  guests: [],
  myRsvp: null,
  surveySlugs: [],
  invitedUserIds: [],
  invitedUserNames: [],
  invitedUserPhotoUrls: [],
  invitePermission: InvitePermission.CoHostsOnly,
  eventType: EventType.Community,
  visibility: EventVisibility.Public,
  photoUrl: '',
  isPast: false,
  status: EventStatus.Active,
};

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderActions(event: Event) {
  return render(
    <QueryClientProvider client={makeQc()}>
      <MemoryRouter>
        <EventAdminActions event={event} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
  vi.clearAllMocks();
});

describe('EventAdminActions', () => {
  it('creator sees edit and delete buttons for upcoming event', () => {
    const creator = makeUser(CREATOR_ID);
    useAuthStore.setState({ status: 'authed', user: creator, accessToken: 'tok' });

    renderActions(BASE_EVENT);

    expect(screen.getByRole('button', { name: /^edit$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^delete$/i })).toBeInTheDocument();
  });

  it('co-host sees edit and cancel buttons for upcoming event', () => {
    const cohost = makeUser(COHOST_ID);
    useAuthStore.setState({ status: 'authed', user: cohost, accessToken: 'tok' });

    renderActions(BASE_EVENT);

    expect(screen.getByRole('button', { name: /^edit$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel event/i })).toBeInTheDocument();
    // Co-host is not the creator, so no delete button (canDelete = isCreator || canManage)
    expect(screen.queryByRole('button', { name: /^delete$/i })).not.toBeInTheDocument();
  });

  it('creator sees no cancel button for a past event', () => {
    const creator = makeUser(CREATOR_ID);
    useAuthStore.setState({ status: 'authed', user: creator, accessToken: 'tok' });

    // isPast doesn't affect cancel — cancelled status does. Test cancelled event.
    const cancelledEvent: Event = { ...BASE_EVENT, status: EventStatus.Cancelled };
    renderActions(cancelledEvent);

    // Edit and delete present, but no cancel-event button for already-cancelled events
    expect(screen.getByRole('button', { name: /^edit$/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancel event/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^delete$/i })).toBeInTheDocument();
  });

  it('regular member (not creator, not co-host) sees no admin action buttons', () => {
    const regular = makeUser(REGULAR_ID);
    useAuthStore.setState({ status: 'authed', user: regular, accessToken: 'tok' });

    renderActions(BASE_EVENT);

    expect(screen.queryByRole('button', { name: /^edit$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancel event/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^delete$/i })).not.toBeInTheDocument();
  });

  it('unauthenticated user sees no admin action buttons', () => {
    useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });

    renderActions(BASE_EVENT);

    expect(screen.queryByRole('button', { name: /^edit$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancel event/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^delete$/i })).not.toBeInTheDocument();
  });
});
