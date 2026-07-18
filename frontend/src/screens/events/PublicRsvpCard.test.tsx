import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import {
  type Event,
  EventStatus,
  EventType,
  EventVisibility,
  InvitePermission,
  RsvpServerStatus,
} from '@/models/event';

const updateMutate = vi.fn();
const cancelMutate = vi.fn();
vi.mock('@/api/publicRsvp', () => ({
  useUpdatePublicMyRsvp: () => ({ mutateAsync: updateMutate, isPending: false }),
  useCancelPublicMyRsvp: () => ({ mutateAsync: cancelMutate, isPending: false }),
}));

import { PublicRsvpCard } from './PublicRsvpCard';

function makeEvent(overrides: Partial<Event>): Event {
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
    allowPlusOnes: true,
    maxAttendees: null,
    attendingCount: 0,
    waitlistedCount: 0,
    invitedCount: 0,
    datetimeTbd: false,
    hasPoll: false,
    datetimePollSlug: null,
    createdById: 'user-host',
    createdByName: 'Host',
    createdByPhotoUrl: '',
    coHostIds: [],
    coHostNames: [],
    coHostPhotoUrls: [],
    coHostInviteIds: [],
    guests: [],
    myRsvp: null,
    viewerUserId: null,
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
    photoUpdatedAt: null,
    tags: [],
    isPast: false,
    status: EventStatus.Active,
    ...overrides,
  };
}

function renderCard(props: { status: string; hasPlusOne: boolean; event?: Partial<Event> }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <PublicRsvpCard
          token="tok123"
          event={makeEvent(props.event ?? {})}
          status={props.status}
          hasPlusOne={props.hasPlusOne}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('PublicRsvpCard', () => {
  it('links the event title to the event detail page with the rsvp token', () => {
    renderCard({ status: RsvpServerStatus.Attending, hasPlusOne: false, event: { id: 'ev1' } });
    expect(screen.getByRole('link', { name: 'Potluck' })).toHaveAttribute(
      'href',
      '/events/ev1?rsvp_token=tok123',
    );
  });

  it('shows the +1 toggle when attending', () => {
    renderCard({ status: RsvpServerStatus.Attending, hasPlusOne: false });
    expect(screen.getByRole('switch', { name: /bring a \+1/i })).toBeInTheDocument();
  });

  it('keeps the +1 toggle visible and checked after switching to maybe', () => {
    renderCard({ status: RsvpServerStatus.Attending, hasPlusOne: true });
    fireEvent.click(screen.getByRole('button', { name: /^maybe$/i }));
    expect(updateMutate).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpServerStatus.Maybe, hasPlusOne: true }),
    );
  });

  it('preserves the +1 flag when switching to can’t go', () => {
    renderCard({ status: RsvpServerStatus.Attending, hasPlusOne: true });
    fireEvent.click(screen.getByRole('button', { name: /can't go/i }));
    expect(updateMutate).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpServerStatus.CantGo, hasPlusOne: true }),
    );
  });

  it('allows toggling +1 while on maybe', () => {
    renderCard({ status: RsvpServerStatus.Maybe, hasPlusOne: false });
    fireEvent.click(screen.getByRole('switch', { name: /bring a \+1/i }));
    expect(updateMutate).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpServerStatus.Maybe, hasPlusOne: true }),
    );
  });

  it('hides the +1 toggle when waitlisted', () => {
    renderCard({ status: RsvpServerStatus.Waitlisted, hasPlusOne: false });
    expect(screen.queryByRole('switch', { name: /bring a \+1/i })).not.toBeInTheDocument();
  });

  it('hides the +1 toggle when the event does not allow plus ones', () => {
    renderCard({
      status: RsvpServerStatus.Attending,
      hasPlusOne: false,
      event: { allowPlusOnes: false },
    });
    expect(screen.queryByRole('switch', { name: /bring a \+1/i })).not.toBeInTheDocument();
  });
});
