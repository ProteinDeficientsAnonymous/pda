import { describe, expect, it } from 'vitest';

import { RsvpServerStatus } from '@/models/event';
import { makeEvent, makeGuest } from '@/test/fixtures';

import { mapEvent, mapEventGuests, mergeEventGuestPhotos, type WireEvent } from './eventMapper';

function wireEvent(overrides: Partial<WireEvent> = {}): WireEvent {
  return {
    id: 'abc-123',
    title: 'Vegan Potluck',
    start_datetime: '2026-04-15T18:00:00Z',
    ...overrides,
  };
}

describe('mapEvent', () => {
  it('maps required fields', () => {
    const result = mapEvent(wireEvent());
    expect(result.id).toBe('abc-123');
    expect(result.title).toBe('Vegan Potluck');
    expect(result.startDatetime).toBeInstanceOf(Date);
    expect(result.startDatetime!.getUTCHours()).toBe(18);
  });

  it('maps my_paid_confirmed', () => {
    expect(mapEvent(wireEvent({ my_paid_confirmed: true })).myPaidConfirmed).toBe(true);
  });

  it('defaults myPaidConfirmed to false when absent', () => {
    expect(mapEvent(wireEvent()).myPaidConfirmed).toBe(false);
  });

  it('maps paid_confirmed on guests', () => {
    const result = mapEvent(
      wireEvent({
        guests: [
          { user_id: 'u1', name: 'Paid Guest', status: 'attending', paid_confirmed: true },
          { user_id: 'u2', name: 'Unpaid Guest', status: 'attending' },
        ],
      }),
    );
    expect(result.guests[0]!.paidConfirmed).toBe(true);
    expect(result.guests[1]!.paidConfirmed).toBe(false);
  });

  it('should map rsvp_questions and my_questionnaire_responses', () => {
    const result = mapEvent(
      wireEvent({
        rsvp_questions: [
          {
            id: 'q1',
            label: 'dietary?',
            field_type: 'textarea',
            options: [],
            required: true,
          },
        ],
        my_questionnaire_responses: { q1: { label: 'dietary?', answer: 'none' } },
      }),
    );
    expect(result.rsvpQuestions).toEqual([
      {
        id: 'q1',
        label: 'dietary?',
        fieldType: 'textarea',
        options: [],
        required: true,
      },
    ]);
    expect(result.myQuestionnaireResponses).toEqual({
      q1: { label: 'dietary?', answer: 'none' },
    });
  });

  it('converts ISO start_datetime to Date', () => {
    const result = mapEvent(wireEvent({ start_datetime: '2026-01-05T09:05:03Z' }));
    expect(result.startDatetime!.getUTCFullYear()).toBe(2026);
    expect(result.startDatetime!.getUTCMonth()).toBe(0);
    expect(result.startDatetime!.getUTCDate()).toBe(5);
  });

  it('converts end_datetime to Date when present', () => {
    const result = mapEvent(wireEvent({ end_datetime: '2026-04-15T21:00:00Z' }));
    expect(result.endDatetime).toBeInstanceOf(Date);
    expect(result.endDatetime!.getUTCHours()).toBe(21);
  });

  it('sets endDatetime to null when absent', () => {
    const result = mapEvent(wireEvent({ end_datetime: null }));
    expect(result.endDatetime).toBeNull();
  });

  it('defaults string fields to empty string', () => {
    const result = mapEvent(wireEvent());
    expect(result.description).toBe('');
    expect(result.location).toBe('');
    expect(result.whatsappLink).toBe('');
    expect(result.partifulLink).toBe('');
    expect(result.otherLink).toBe('');
    expect(result.venmoLink).toBe('');
    expect(result.cashappLink).toBe('');
    expect(result.zelleInfo).toBe('');
    expect(result.price).toBe('');
    expect(result.photoUrl).toBe('');
  });

  it('defaults boolean fields to false', () => {
    const result = mapEvent(wireEvent());
    expect(result.rsvpEnabled).toBe(false);
    expect(result.allowPlusOnes).toBe(false);
    expect(result.datetimeTbd).toBe(false);
    expect(result.hasPoll).toBe(false);
  });

  it('defaults numeric counts to 0', () => {
    const result = mapEvent(wireEvent());
    expect(result.attendingCount).toBe(0);
    expect(result.waitlistedCount).toBe(0);
    expect(result.invitedCount).toBe(0);
  });

  it('defaults array fields to empty arrays', () => {
    const result = mapEvent(wireEvent());
    expect(result.guests).toEqual([]);
    expect(result.surveySlugs).toEqual([]);
    expect(result.coHostIds).toEqual([]);
    expect(result.invitedUserIds).toEqual([]);
    expect(result.invitedUserNames).toEqual([]);
  });

  it('defaults eventType to community', () => {
    const result = mapEvent(wireEvent());
    expect(result.eventType).toBe('community');
  });

  it('defaults visibility to public', () => {
    const result = mapEvent(wireEvent());
    expect(result.visibility).toBe('public');
  });

  it('defaults isPast to false', () => {
    const result = mapEvent(wireEvent());
    expect(result.isPast).toBe(false);
  });

  it('defaults status to active', () => {
    const result = mapEvent(wireEvent());
    expect(result.status).toBe('active');
  });

  it('maps provided optional fields through', () => {
    const result = mapEvent(
      wireEvent({
        description: 'Bring food!',
        location: 'Central Park',
        whatsapp_link: 'https://chat.whatsapp.com/abc',
        event_type: 'official',
        visibility: 'members_only',
        is_past: true,
      }),
    );
    expect(result.description).toBe('Bring food!');
    expect(result.location).toBe('Central Park');
    expect(result.whatsappLink).toBe('https://chat.whatsapp.com/abc');
    expect(result.eventType).toBe('official');
    expect(result.visibility).toBe('members_only');
    expect(result.isPast).toBe(true);
  });

  it('maps nested guests array', () => {
    const result = mapEvent(
      wireEvent({
        guests: [
          {
            user_id: 'u1',
            name: 'Alice',
            status: 'attending',
            phone: '+447700000000',
            photo_url: 'https://example.com/photo.jpg',
            has_plus_one: true,
          },
        ],
      }),
    );
    expect(result.guests).toHaveLength(1);
    const guest = result.guests[0]!;
    expect(guest.userId).toBe('u1');
    expect(guest.name).toBe('Alice');
    expect(guest.status).toBe('attending');
    expect(guest.phone).toBe('+447700000000');
    expect(guest.photoUrl).toBe('https://example.com/photo.jpg');
    expect(guest.hasPlusOne).toBe(true);
  });

  it('defaults guest optional fields', () => {
    const result = mapEvent(
      wireEvent({
        guests: [{ user_id: 'u2', name: 'Bob', status: 'maybe' }],
      }),
    );
    const guest = result.guests[0]!;
    expect(guest.phone).toBeNull();
    expect(guest.photoUrl).toBe('');
    expect(guest.hasPlusOne).toBe(false);
  });
});

describe('mapEventGuests', () => {
  it('should map guests and invited photos', () => {
    const result = mapEventGuests({
      guests: [
        { user_id: 'u1', name: 'Alex', status: 'attending', photo_url: 'https://cdn/a.jpg' },
      ],
      invited_user_ids: ['u2'],
      invited_user_names: ['Sam'],
      invited_user_photo_urls: ['https://cdn/s.jpg'],
    });
    expect(result.guests[0]).toMatchObject({ userId: 'u1', photoUrl: 'https://cdn/a.jpg' });
    expect(result.invitedUserPhotoUrls).toEqual(['https://cdn/s.jpg']);
  });
});

describe('mergeEventGuestPhotos', () => {
  it('should keep live guest name and status when the photos payload is stale', () => {
    const event = makeEvent({
      guests: [
        makeGuest({
          userId: 'u1',
          name: 'Alex',
          status: RsvpServerStatus.Attending,
          photoUrl: '',
          hasPlusOne: true,
        }),
        makeGuest({ userId: 'u-new', name: 'Just added', photoUrl: '' }),
      ],
      invitedUserIds: ['inv-1'],
      invitedUserNames: ['Sam'],
      invitedUserPhotoUrls: ['https://cdn/sam.jpg'],
    });
    const photos = {
      guests: [
        makeGuest({
          userId: 'u1',
          name: 'Stale Alex',
          status: RsvpServerStatus.Maybe,
          photoUrl: 'https://cdn/alex.jpg',
        }),
      ],
    };
    const merged = mergeEventGuestPhotos(event, photos);
    expect(merged.guests.map((g) => g.userId)).toEqual(['u1', 'u-new']);
    expect(merged.guests[0]).toMatchObject({
      name: 'Alex',
      status: RsvpServerStatus.Attending,
      hasPlusOne: true,
      photoUrl: 'https://cdn/alex.jpg',
    });
    expect(merged.guests[1]!.name).toBe('Just added');
    expect(merged.invitedUserIds).toEqual(['inv-1']);
    expect(merged.invitedUserNames).toEqual(['Sam']);
    expect(merged.invitedUserPhotoUrls).toEqual(['https://cdn/sam.jpg']);
  });

  it('should clear a leftover preview photo when the guests payload has an empty url', () => {
    const event = makeEvent({
      guests: [makeGuest({ userId: 'u1', photoUrl: 'https://cdn/old.jpg' })],
    });
    const merged = mergeEventGuestPhotos(event, {
      guests: [makeGuest({ userId: 'u1', photoUrl: '' })],
    });
    expect(merged.guests[0]!.photoUrl).toBe('');
  });

  it('should return the event unchanged when guests have not loaded', () => {
    const event = makeEvent({ guests: [makeGuest({ userId: 'u1' })] });
    expect(mergeEventGuestPhotos(event, undefined)).toBe(event);
  });
});
