import { describe, it, expect } from 'vitest';
import { mapEvent, type WireEvent } from './eventMapper';

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
    expect(result.startDatetime.getUTCHours()).toBe(18);
  });

  it('converts ISO start_datetime to Date', () => {
    const result = mapEvent(wireEvent({ start_datetime: '2026-01-05T09:05:03Z' }));
    expect(result.startDatetime.getUTCFullYear()).toBe(2026);
    expect(result.startDatetime.getUTCMonth()).toBe(0);
    expect(result.startDatetime.getUTCDate()).toBe(5);
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
    const guest = result.guests[0];
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
    const guest = result.guests[0];
    expect(guest.phone).toBeNull();
    expect(guest.photoUrl).toBe('');
    expect(guest.hasPlusOne).toBe(false);
  });
});
