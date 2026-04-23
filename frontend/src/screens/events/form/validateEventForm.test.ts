import { describe, it, expect } from 'vitest';
import type { EventFormValues } from '@/api/eventWrites';
import { validateEventForm } from './validateEventForm';

function validValues(overrides: Partial<EventFormValues> = {}): EventFormValues {
  const futureDate = new Date(Date.now() + 60 * 60 * 1000).toISOString(); // 1h from now
  return {
    title: 'Vegan Potluck',
    description: '',
    location: '',
    latitude: null,
    longitude: null,
    startDatetime: futureDate,
    endDatetime: null,
    datetimeTbd: false,
    eventType: 'community',
    visibility: 'public',
    visibilityChoice: 'public',
    invitePermission: 'all_members',
    rsvpEnabled: false,
    allowPlusOnes: false,
    maxAttendees: null,
    whatsappLink: '',
    partifulLink: '',
    otherLink: '',
    price: '',
    venmoLink: '',
    cashappLink: '',
    zelleInfo: '',
    coHostIds: [],
    invitedUserIds: [],
    status: 'active',
    ...overrides,
  };
}

describe('validateEventForm', () => {
  it('returns no errors for valid values', () => {
    expect(validateEventForm(validValues())).toEqual({});
  });

  describe('title', () => {
    it('requires a non-empty title', () => {
      const errors = validateEventForm(validValues({ title: '' }));
      expect(errors.title).toBe('required');
    });

    it('requires a non-whitespace title', () => {
      const errors = validateEventForm(validValues({ title: '   ' }));
      expect(errors.title).toBe('required');
    });

    it('rejects title over 200 characters', () => {
      const errors = validateEventForm(validValues({ title: 'a'.repeat(201) }));
      expect(errors.title).toBe('under 200 chars');
    });

    it('accepts title at exactly 200 characters', () => {
      const errors = validateEventForm(validValues({ title: 'a'.repeat(200) }));
      expect(errors.title).toBeUndefined();
    });
  });

  describe('description', () => {
    it('rejects description over 2000 characters', () => {
      const errors = validateEventForm(validValues({ description: 'a'.repeat(2001) }));
      expect(errors.description).toBe('too long');
    });

    it('accepts description at exactly 2000 characters', () => {
      const errors = validateEventForm(validValues({ description: 'a'.repeat(2000) }));
      expect(errors.description).toBeUndefined();
    });
  });

  describe('location', () => {
    it('rejects location over 300 characters', () => {
      const errors = validateEventForm(validValues({ location: 'a'.repeat(301) }));
      expect(errors.location).toBe('under 300 chars');
    });
  });

  describe('startDatetime', () => {
    it('requires startDatetime on active events when not TBD', () => {
      const errors = validateEventForm(
        validValues({ startDatetime: '', datetimeTbd: false, status: 'active' }),
      );
      expect(errors.startDatetime).toBe('required');
    });

    it('does not require startDatetime on drafts (progress-capture)', () => {
      const errors = validateEventForm(
        validValues({ startDatetime: '', datetimeTbd: false, status: 'draft' }),
      );
      expect(errors.startDatetime).toBeUndefined();
    });

    it('does not require startDatetime when datetimeTbd is true', () => {
      const errors = validateEventForm(validValues({ startDatetime: '', datetimeTbd: true }));
      expect(errors.startDatetime).toBeUndefined();
    });

    it('rejects startDatetime in the past for active events', () => {
      const past = new Date(Date.now() - 5 * 60 * 1000).toISOString(); // 5 min ago
      const errors = validateEventForm(validValues({ startDatetime: past, status: 'active' }));
      expect(errors.startDatetime).toBe('start must be in the future');
    });

    it('rejects startDatetime in the past for drafts too (once a date is picked)', () => {
      const past = new Date(Date.now() - 5 * 60 * 1000).toISOString();
      const errors = validateEventForm(validValues({ startDatetime: past, status: 'draft' }));
      expect(errors.startDatetime).toBe('start must be in the future');
    });
  });

  describe('endDatetime', () => {
    it('rejects endDatetime not after startDatetime', () => {
      const start = new Date(Date.now() + 60 * 60 * 1000).toISOString();
      const end = new Date(Date.now() + 30 * 60 * 1000).toISOString(); // before start
      const errors = validateEventForm(validValues({ startDatetime: start, endDatetime: end }));
      expect(errors.endDatetime).toBe('end must be after start');
    });

    it('rejects endDatetime equal to startDatetime', () => {
      const dt = new Date(Date.now() + 60 * 60 * 1000).toISOString();
      const errors = validateEventForm(validValues({ startDatetime: dt, endDatetime: dt }));
      expect(errors.endDatetime).toBe('end must be after start');
    });

    it('accepts null endDatetime', () => {
      const errors = validateEventForm(validValues({ endDatetime: null }));
      expect(errors.endDatetime).toBeUndefined();
    });
  });

  describe('maxAttendees', () => {
    it('rejects negative maxAttendees', () => {
      const errors = validateEventForm(validValues({ maxAttendees: -1 }));
      expect(errors.maxAttendees).toBe('must be 0 or more');
    });

    it('accepts zero maxAttendees', () => {
      const errors = validateEventForm(validValues({ maxAttendees: 0 }));
      expect(errors.maxAttendees).toBeUndefined();
    });

    it('accepts null maxAttendees', () => {
      const errors = validateEventForm(validValues({ maxAttendees: null }));
      expect(errors.maxAttendees).toBeUndefined();
    });
  });
});
