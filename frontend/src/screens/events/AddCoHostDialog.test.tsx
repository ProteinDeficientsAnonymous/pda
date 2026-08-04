import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { Event } from '@/models/event';
import { EventStatus, EventType, EventVisibility, InvitePermission } from '@/models/event';

import { AddCoHostDialog } from './AddCoHostDialog';

const updateMutateAsync = vi.hoisted(() => vi.fn());

vi.mock('@/api/eventWrites', () => ({
  useUpdateEvent: () => ({ mutateAsync: updateMutateAsync, isPending: false }),
}));

vi.mock('@/api/userSearch', () => ({
  useUserSearch: () => ({
    data: [
      { id: 'user-accepted', fullName: 'Accepted Host', phoneNumber: '5551110000' },
      { id: 'user-pending', fullName: 'Pending Invitee', phoneNumber: '5552220000' },
      { id: 'user-available', fullName: 'Available Member', phoneNumber: '5553330000' },
    ],
  }),
}));

const BASE_EVENT: Event = {
  id: 'ev1',
  slug: 'spring-potluck',
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
  coHostIds: ['user-creator', 'user-accepted'],
  coHostNames: [],
  coHostPhotoUrls: [],
  guests: [],
  myRsvp: null,
  viewerUserId: null,
  surveySlugs: [],
  invitedUserIds: [],
  invitedUserNames: [],
  invitedUserPhotoUrls: [],
  invitePermission: InvitePermission.AllMembers,
  pendingCohostInvites: [
    {
      id: 'inv1',
      userId: 'user-pending',
      userName: 'Pending Invitee',
      userPhotoUrl: '',
      invitedAt: new Date(),
    },
  ],
  myPendingCohostInviteId: null,
  eventType: EventType.Community,
  visibility: EventVisibility.Public,
  photoUrl: '',
  photoUpdatedAt: null,
  tags: [],
  isPast: false,
  status: EventStatus.Active,
};

describe('AddCoHostDialog', () => {
  it('excludes members with a pending cohost invite from search results', () => {
    render(<AddCoHostDialog event={BASE_EVENT} open onClose={() => {}} />);

    fireEvent.change(screen.getByLabelText('search members'), { target: { value: 'me' } });

    expect(screen.getByText('Available Member')).toBeInTheDocument();
    expect(screen.queryByText('Pending Invitee')).not.toBeInTheDocument();
    expect(screen.queryByText('Accepted Host')).not.toBeInTheDocument();
  });
});
