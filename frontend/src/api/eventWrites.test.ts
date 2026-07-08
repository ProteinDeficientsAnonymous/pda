// Pure-helper tests for the event write layer: enum-coercion on the inbound
// side (eventToFormValues) and per-field PATCH body building (toPartialWireBody).
import { describe, expect,it } from 'vitest';

import {
  type Event,
  EventStatus,
  EventType,
  EventVisibility,
  InvitePermission,
} from '@/models/event';

import { eventToFormValues, toPartialWireBody } from './eventWrites';

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 'e1',
    title: 'potluck',
    description: 'bring food',
    startDatetime: new Date('2026-06-01T18:00:00Z'),
    endDatetime: new Date('2026-06-01T20:00:00Z'),
    location: 'the park',
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
    createdById: null,
    createdByName: null,
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
    tags: [],
    isPast: false,
    status: EventStatus.Active,
    ...overrides,
  };
}

describe('eventToFormValues enum validation', () => {
  it('passes through known enum values', () => {
    const form = eventToFormValues(
      makeEvent({
        eventType: EventType.Official,
        visibility: EventVisibility.MembersOnly,
        invitePermission: InvitePermission.CoHostsOnly,
        status: EventStatus.Cancelled,
      }),
    );
    expect(form.eventType).toBe('official');
    expect(form.visibility).toBe('members_only');
    expect(form.invitePermission).toBe('co_hosts_only');
    expect(form.status).toBe('cancelled');
  });

  it('falls back to safe defaults on unknown enum values', () => {
    const form = eventToFormValues(
      makeEvent({
        eventType: 'galaxy_brain',
        visibility: 'top_secret',
        invitePermission: 'nobody',
        status: 'quantum',
      }),
    );
    expect(form.eventType).toBe(EventType.Community);
    expect(form.visibility).toBe(EventVisibility.Public);
    expect(form.invitePermission).toBe(InvitePermission.AllMembers);
    expect(form.status).toBe(EventStatus.Active);
  });

  it('derives visibilityChoice from the coerced (not raw) values', () => {
    const form = eventToFormValues(makeEvent({ eventType: 'bogus', visibility: 'bogus' }));
    // community + public → 'public'
    expect(form.visibilityChoice).toBe('public');
  });

  it('maps tags to tagIds', () => {
    const form = eventToFormValues(
      makeEvent({
        tags: [
          { id: 't1', name: 'walk', slug: 'walk' },
          { id: 't2', name: 'restaurant meetup', slug: 'restaurant-meetup' },
        ],
      }),
    );
    expect(form.tagIds).toEqual(['t1', 't2']);
  });
});

describe('toPartialWireBody', () => {
  it('only includes keys present in the partial', () => {
    const body = toPartialWireBody({ title: 'new title' });
    expect(body).toEqual({ title: 'new title' });
  });

  it('keeps meaningful falsy values (false, "", null)', () => {
    const body = toPartialWireBody({ rsvpEnabled: false, price: '', maxAttendees: null });
    expect(body).toEqual({ rsvp_enabled: false, price: '', max_attendees: null });
  });

  it('drops explicitly-undefined keys', () => {
    const body = toPartialWireBody({ title: 'x', description: undefined });
    expect(body).toEqual({ title: 'x' });
  });

  it('expands visibilityChoice into visibility + event_type', () => {
    expect(toPartialWireBody({ visibilityChoice: 'official' })).toEqual({
      visibility: 'public',
      event_type: 'official',
    });
    expect(toPartialWireBody({ visibilityChoice: 'invite_only' })).toEqual({
      visibility: 'invite_only',
      event_type: 'community',
    });
  });

  it('maps camelCase keys to their snake_case wire keys with transforms', () => {
    const body = toPartialWireBody({ startDatetime: '2026-06-01T00:00:00Z', venmoLink: 'leah' });
    expect(body.start_datetime).toBe('2026-06-01T00:00:00Z');
    // venmoLink is run through toVenmoUrl — the bare handle becomes a full url.
    expect(typeof body.venmo_link).toBe('string');
    expect(body.venmo_link).toContain('leah');
  });

  it('maps tagIds to tag_ids, including an empty list (clears tags)', () => {
    expect(toPartialWireBody({ tagIds: ['t1', 't2'] })).toEqual({ tag_ids: ['t1', 't2'] });
    expect(toPartialWireBody({ tagIds: [] })).toEqual({ tag_ids: [] });
  });
});
