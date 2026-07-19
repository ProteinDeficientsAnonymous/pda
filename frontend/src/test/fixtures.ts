import type { EventAttendanceRow } from '@/api/attendanceReport';
import type { JoinRequestSummary } from '@/api/join';
import { JoinRequestStatus } from '@/api/join';
import type { Member } from '@/api/users';
import type { Event, EventGuest } from '@/models/event';
import {
  AttendanceStatus,
  EventStatus,
  EventType,
  EventVisibility,
  InvitePermission,
  RsvpServerStatus,
} from '@/models/event';
import type { AppNotification } from '@/models/notification';
import { NotificationType } from '@/models/notification';
import type { User } from '@/models/user';

export function makeGuest(overrides: Partial<EventGuest> = {}): EventGuest {
  return {
    userId: 'user-other',
    name: 'Other',
    status: RsvpServerStatus.Attending,
    phone: null,
    photoUrl: '',
    hasPlusOne: false,
    attendance: AttendanceStatus.Unknown,
    isMember: true,
    ...overrides,
  };
}

export function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 'ev1',
    title: 'Test Event',
    description: '',
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
    rsvpEnabled: true,
    allowPlusOnes: false,
    maxAttendees: null,
    attendingCount: 1,
    waitlistedCount: 0,
    invitedCount: 0,
    datetimeTbd: false,
    hasPoll: false,
    datetimePollSlug: null,
    createdById: 'creator',
    createdByName: 'Creator',
    createdByPhotoUrl: '',
    coHostIds: [],
    coHostNames: [],
    coHostPhotoUrls: [],
    coHostInviteIds: [],
    guests: [
      {
        userId: 'a',
        name: 'alice',
        status: RsvpServerStatus.Attending,
        phone: '+15551112222',
        photoUrl: '',
        hasPlusOne: false,
        attendance: AttendanceStatus.Unknown,
        isMember: true,
      },
      {
        userId: 'b',
        name: 'bob',
        status: RsvpServerStatus.CantGo,
        phone: '+15553334444',
        photoUrl: '',
        hasPlusOne: false,
        isMember: true,
        attendance: AttendanceStatus.Unknown,
      },
    ],
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

export function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 'user1',
    phoneNumber: '+12125550001',
    firstName: 'Test',
    lastName: 'User',
    fullName: 'Test User',
    nickname: '',
    email: '',
    bio: '',
    pronouns: '',
    birthday: null,
    isSuperuser: false,
    isStaff: false,
    needsOnboarding: false,
    needsPasswordReset: false,
    needsGuidelinesConsent: false,
    needsSmsConsent: false,
    needsContactPrivacyConsent: false,
    showPhone: false,
    showEmail: false,
    showBirthday: false,
    hideLastName: false,
    weekStart: 'sunday',
    calendarFeedScope: 'all',
    profilePhotoUrl: '',
    photoUpdatedAt: null,
    roles: [],
    ...overrides,
  };
}

export function makeMember(overrides: Partial<Member> = {}): Member {
  return {
    id: 'member-1',
    firstName: 'Ada',
    lastName: '',
    fullName: 'Ada',
    phoneNumber: '+15551230001',
    email: '',
    bio: '',
    profilePhotoUrl: '',
    showPhone: true,
    showEmail: true,
    isMember: true,
    isSuperuser: false,
    isPaused: false,
    needsOnboarding: false,
    loginLinkRequested: false,
    lastAttendedAt: null,
    roles: [],
    ...overrides,
  };
}

export function makeRequest(overrides: Partial<JoinRequestSummary> = {}): JoinRequestSummary {
  return {
    id: 'jr-1',
    fullName: 'Ada Lovelace',
    phoneNumber: '+16505550001',
    email: 'ada@example.com',
    answers: [],
    submittedAt: '2026-01-01T00:00:00Z',
    status: JoinRequestStatus.PENDING,
    userId: null,
    previouslyArchived: false,
    approvedAt: null,
    approvedByName: null,
    rejectedAt: null,
    rejectedByName: null,
    onboardedAt: null,
    rsvpBreakdown: {
      attendedOfficial: 0,
      attendedClub: 0,
      upcomingOfficial: 0,
      upcomingClub: 0,
    },
    rsvpEvents: [],
    ...overrides,
  };
}

export function makeRow(overrides: Partial<EventAttendanceRow> = {}): EventAttendanceRow {
  return {
    eventId: 'e1',
    title: 'Potluck',
    startDatetime: new Date('2026-03-15T18:00:00Z'),
    attendedCount: 4,
    noShowCount: 1,
    goingCount: 6,
    ...overrides,
  };
}

export function makeNotification(id: string, message: string, isRead = false): AppNotification {
  return {
    id,
    notificationType: NotificationType.EventInvite,
    eventId: 'evt1',
    relatedUserId: null,
    message,
    isRead,
    createdAt: '2024-01-01T00:00:00Z',
  };
}
