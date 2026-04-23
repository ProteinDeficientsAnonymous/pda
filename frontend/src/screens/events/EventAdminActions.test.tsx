import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import { EventStatus, EventType, EventVisibility, InvitePermission } from '@/models/event';
import type { User } from '@/models/user';

// Mock network-touching dependencies
vi.mock('@/api/eventWrites', () => ({
  useUpdateEvent: vi.fn().mockReturnValue({ mutateAsync: vi.fn(), isPending: false }),
  useCancelEvent: vi.fn().mockReturnValue({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteEvent: vi.fn().mockReturnValue({ mutateAsync: vi.fn(), isPending: false }),
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
    roles: permissions.length ? [{ id: 'r1', name: 'custom', isDefault: true, permissions }] : [],
  };
}

const BASE_EVENT: Event = {
  id: 'ev1',
  title: 'Test Event',
  description: '',
  // Upcoming by default — individual tests override for past/just-ended cases.
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
  rsvpEnabled: false,
  allowPlusOnes: false,
  maxAttendees: null,
  attendingCount: 3,
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
  it('creator sees edit and cancel (no delete) for active upcoming event with attendees', () => {
    const creator = makeUser(CREATOR_ID);
    useAuthStore.setState({ status: 'authed', user: creator, accessToken: 'tok' });

    renderActions(BASE_EVENT);

    expect(screen.getByRole('button', { name: /^edit$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel event/i })).toBeInTheDocument();
    // With attendees, the event must be cancelled before it can be deleted.
    expect(screen.queryByRole('button', { name: /^delete$/i })).not.toBeInTheDocument();
  });

  // With no one RSVP'd, skip the cancel-then-delete two-step: show delete outright.
  it('creator sees delete (no cancel) for active upcoming event with no attendees', () => {
    const creator = makeUser(CREATOR_ID);
    useAuthStore.setState({ status: 'authed', user: creator, accessToken: 'tok' });

    const emptyEvent: Event = { ...BASE_EVENT, attendingCount: 0 };
    renderActions(emptyEvent);

    expect(screen.getByRole('button', { name: /^edit$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^delete$/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancel event/i })).not.toBeInTheDocument();
  });

  it('creator sees delete for draft event', () => {
    const creator = makeUser(CREATOR_ID);
    useAuthStore.setState({ status: 'authed', user: creator, accessToken: 'tok' });

    const draftEvent: Event = { ...BASE_EVENT, status: EventStatus.Draft };
    renderActions(draftEvent);

    expect(screen.getByRole('button', { name: /^edit$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^publish$/i })).toBeInTheDocument();
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

  // A draft event with attendees still shows delete: drafts haven't been
  // published, so there's nothing to cancel — users can delete directly.
  it('creator sees delete for draft event regardless of attendees count', () => {
    const creator = makeUser(CREATOR_ID);
    useAuthStore.setState({ status: 'authed', user: creator, accessToken: 'tok' });

    const draftWithAttendees: Event = {
      ...BASE_EVENT,
      status: EventStatus.Draft,
      attendingCount: 5,
    };
    renderActions(draftWithAttendees);

    expect(screen.getByRole('button', { name: /^delete$/i })).toBeInTheDocument();
  });

  // Past events can't be edited (would change historical record). Delete is
  // still allowed on cancelled past events; cancel button hidden since it's
  // already cancelled.
  it('creator sees only delete (no edit) for a past cancelled event', () => {
    const creator = makeUser(CREATOR_ID);
    useAuthStore.setState({ status: 'authed', user: creator, accessToken: 'tok' });

    const pastCancelled: Event = {
      ...BASE_EVENT,
      // A full day ago — well past the 6-hour grace window.
      startDatetime: new Date(Date.now() - 24 * 60 * 60 * 1000),
      isPast: true,
      status: EventStatus.Cancelled,
    };
    renderActions(pastCancelled);

    expect(screen.queryByRole('button', { name: /^edit$/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^delete$/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancel event/i })).not.toBeInTheDocument();
  });

  // 6-hour grace window: hosts can still fix typos / tweak details during and
  // just after the event.
  it('creator can still edit an event that started 2 hours ago (within grace window)', () => {
    const creator = makeUser(CREATOR_ID);
    useAuthStore.setState({ status: 'authed', user: creator, accessToken: 'tok' });

    const justStarted: Event = {
      ...BASE_EVENT,
      startDatetime: new Date(Date.now() - 2 * 60 * 60 * 1000),
      endDatetime: null,
      isPast: true,
    };
    renderActions(justStarted);

    expect(screen.getByRole('button', { name: /^edit$/i })).toBeInTheDocument();
  });

  it('creator cannot edit an event that ended 10 hours ago (past grace window)', () => {
    const creator = makeUser(CREATOR_ID);
    useAuthStore.setState({ status: 'authed', user: creator, accessToken: 'tok' });

    const longOver: Event = {
      ...BASE_EVENT,
      startDatetime: new Date(Date.now() - 12 * 60 * 60 * 1000),
      endDatetime: new Date(Date.now() - 10 * 60 * 60 * 1000),
      isPast: true,
    };
    renderActions(longOver);

    expect(screen.queryByRole('button', { name: /^edit$/i })).not.toBeInTheDocument();
  });

  it('creator uses endDatetime (not startDatetime) as the grace-window anchor', () => {
    const creator = makeUser(CREATOR_ID);
    useAuthStore.setState({ status: 'authed', user: creator, accessToken: 'tok' });

    // Started 4h ago, still going (ends 1h from now). Well within grace.
    const longRunning: Event = {
      ...BASE_EVENT,
      startDatetime: new Date(Date.now() - 4 * 60 * 60 * 1000),
      endDatetime: new Date(Date.now() + 1 * 60 * 60 * 1000),
      isPast: false,
    };
    renderActions(longRunning);

    expect(screen.getByRole('button', { name: /^edit$/i })).toBeInTheDocument();
  });
});
