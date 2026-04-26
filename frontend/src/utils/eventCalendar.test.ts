import { describe, it, expect } from 'vitest';
import type { Event } from '@/models/event';
import { googleCalendarUrl, icsUrl } from './eventCalendar';

describe('googleCalendarUrl', () => {
  it('should return null when event has no start time', () => {
    const e = { startDatetime: null } as Event;
    expect(googleCalendarUrl(e)).toBeNull();
  });

  it('should build a google calendar template url', () => {
    const start = new Date('2026-06-01T18:00:00.000Z');
    const e = {
      id: 'abc-123',
      title: 'potluck',
      startDatetime: start,
      endDatetime: new Date('2026-06-01T20:00:00.000Z'),
      location: 'park',
      description: 'bring food',
      whatsappLink: '',
      partifulLink: '',
      otherLink: '',
    } as Event;
    const url = googleCalendarUrl(e);
    expect(url).toContain('calendar.google.com');
    expect(url?.toLowerCase()).toContain('potluck');
    expect(url).toContain('park');
  });

  it('appends a "View on PDA" link to the description (#347)', () => {
    const start = new Date('2026-06-01T18:00:00.000Z');
    const e = {
      id: 'abc-123',
      title: 'potluck',
      startDatetime: start,
      endDatetime: null,
      location: '',
      description: 'bring food',
      whatsappLink: '',
      partifulLink: '',
      otherLink: '',
    } as Event;
    // `URLSearchParams` encodes spaces as "+", which `decodeURIComponent`
    // doesn't undo — pull the param out via the URL parser instead.
    const details = new URL(googleCalendarUrl(e) ?? '').searchParams.get('details') ?? '';
    expect(details).toContain(`View on PDA: ${window.location.origin}/events/abc-123`);
  });
});

describe('icsUrl', () => {
  it('should point at the backend single-event ics endpoint', () => {
    expect(icsUrl('abc-123')).toBe('/api/community/events/abc-123/ics/');
  });
});
