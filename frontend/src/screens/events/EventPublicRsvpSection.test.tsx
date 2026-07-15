import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import type { Event } from '@/models/event';
import { EventType, EventVisibility, InvitePermission, RsvpServerStatus } from '@/models/event';

import { EventPublicRsvpSection } from './EventPublicRsvpSection';

vi.mock('@/api/eventComments', () => ({
  useEventComments: () => ({
    data: { items: [], canPost: true, cannotPostReason: null },
    isPending: false,
    isError: false,
  }),
  usePostComment: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

function baseEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 'evt-1',
    title: 'Community Potluck',
    description: '',
    startDatetime: new Date('2026-08-01T18:00:00Z'),
    endDatetime: null,
    datetimeTbd: false,
    location: '123 Main St',
    latitude: null,
    longitude: null,
    whatsappLink: 'https://chat.whatsapp.com/abc',
    partifulLink: '',
    otherLink: '',
    price: '',
    venmoLink: '',
    cashappLink: '',
    zelleInfo: '',
    rsvpEnabled: true,
    allowPlusOnes: false,
    maxAttendees: null,
    attendingCount: 1,
    waitlistedCount: 0,
    invitedCount: 0,
    createdById: 'host-1',
    createdByName: 'Host Person',
    createdByPhotoUrl: '',
    coHostIds: [],
    coHostNames: [],
    coHostPhotoUrls: [],
    coHostInviteIds: [],
    pendingCohostInvites: [],
    myPendingCohostInviteId: null,
    guests: [],
    myRsvp: RsvpServerStatus.Attending,
    eventType: EventType.Official,
    visibility: EventVisibility.Public,
    photoUrl: '',
    photoUpdatedAt: null,
    surveySlugs: [],
    datetimePollSlug: null,
    hasPoll: false,
    invitedUserIds: [],
    invitedUserNames: [],
    invitedUserPhotoUrls: [],
    invitePermission: InvitePermission.AllMembers,
    isPast: false,
    status: 'active',
    tags: [],
    ...overrides,
  };
}

function renderSection(event: Event) {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <EventPublicRsvpSection event={event} token="tok-123" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('EventPublicRsvpSection', () => {
  it('shows location and links', () => {
    renderSection(baseEvent());
    expect(screen.getByText('123 Main St')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /whatsapp/i })).toBeInTheDocument();
  });

  it('does not render host edit or admin affordances', () => {
    renderSection(baseEvent());
    expect(screen.queryByText('invite members')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('add co-host')).not.toBeInTheDocument();
  });
});
