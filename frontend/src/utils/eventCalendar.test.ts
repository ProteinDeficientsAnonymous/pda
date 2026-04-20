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
});

describe('icsUrl', () => {
  it('should point at the backend single-event ics endpoint', () => {
    expect(icsUrl('abc-123')).toBe('/api/community/events/abc-123/ics/');
  });
});
