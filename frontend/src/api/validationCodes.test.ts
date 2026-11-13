import { describe, expect, it } from 'vitest';

import { Code, type FieldError, messageForCode, messagesFromFieldErrors } from './validationCodes';

describe('messageForCode', () => {
  it('returns friendly copy for known event-form codes', () => {
    expect(
      messageForCode({
        code: Code.Event.StartDatetimeRequiredUnlessTbd,
        field: 'start_datetime',
      }),
    ).toBe('pick a start time, or mark the time as tbd');
  });

  it('asks for a timezone when an event datetime has no offset', () => {
    expect(
      messageForCode({ code: Code.Event.DatetimeOffsetRequired, field: 'start_datetime' }),
    ).toBe('date and time must include a timezone');
  });

  it('says only official events can have an event format', () => {
    expect(messageForCode({ code: Code.Event.InvalidEventFormat, field: 'event_format' })).toBe(
      'only official events can be a walk or restaurant',
    );
  });

  it('uses the field name for generic fallback codes', () => {
    expect(messageForCode({ code: Code.Generic.FieldRequired, field: 'title' })).toContain('title');
    expect(messageForCode({ code: Code.Generic.FieldInvalid, field: 'max_attendees' })).toContain(
      'max attendees',
    );
  });

  it('interpolates params for password errors', () => {
    const out = messageForCode({
      code: Code.Password.Invalid,
      field: 'password',
      params: { reasons: ['at least 8 chars', 'must contain a number'] },
    });
    expect(out).toContain('at least 8 chars');
    expect(out).toContain('must contain a number');
  });

  it('says a bulk payment verify only covers attending or waitlisted guests', () => {
    expect(messageForCode({ code: Code.Event.PaymentVerifyNotGuests, field: null })).toMatch(
      /attending or waitlisted/,
    );
  });

  it("says only going guests can be marked didn't attend", () => {
    expect(messageForCode({ code: Code.Event.DidntGoRequiresGoing, field: null })).toBe(
      "only guests who rsvp'd going can be marked didn't attend",
    );
  });

  it('says only members can be co-hosts', () => {
    expect(messageForCode({ code: Code.CoHostInvite.NotMember, field: null })).toBe(
      'only members can be co-hosts',
    );
  });

  it('says a host-set guest who cannot sign in cannot be added', () => {
    expect(messageForCode({ code: Code.Event.GuestNotEligible, field: null })).toBe(
      "they can't be added to this event",
    );
  });

  it('says to lift a guidelines pause before an attendance pause', () => {
    expect(messageForCode({ code: Code.User.GuidelinesPaused, field: 'attendance_paused' })).toBe(
      'lift the guidelines pause before pausing for attendance',
    );
  });

  it('says an attendance pause lifts on check-in', () => {
    expect(
      messageForCode({ code: Code.User.AttendancePauseLiftsOnCheckIn, field: 'attendance_paused' }),
    ).toBe('an event rqmt pause lifts when they check in at an official or club event');
  });

  it('explains an empty cash app csv', () => {
    expect(messageForCode({ code: Code.CashAppImport.CsvEmpty, field: null })).toMatch(
      /doesn't have any rows/,
    );
  });

  it('names the missing cash app csv columns when known', () => {
    expect(
      messageForCode({
        code: Code.CashAppImport.CsvMissingColumns,
        field: null,
        params: { columns: 'amount, date' },
      }),
    ).toContain('missing columns: amount, date');
    expect(messageForCode({ code: Code.CashAppImport.CsvMissingColumns, field: null })).toMatch(
      /couldn't read that csv/,
    );
  });

  it('gives the cash app csv row limit when known', () => {
    expect(
      messageForCode({
        code: Code.CashAppImport.CsvTooManyRows,
        field: null,
        params: { max_rows: 10000 },
      }),
    ).toContain('more than 10000 rows');
    expect(messageForCode({ code: Code.CashAppImport.CsvTooManyRows, field: null })).toMatch(
      /too big/,
    );
  });

  it('explains an unsafe photo', () => {
    expect(
      messageForCode({
        code: Code.Photo.Unsafe,
        field: 'photo',
        params: {},
      }),
    ).toMatch(/smaller image/i);
  });

  it('interpolates photo max size', () => {
    const out = messageForCode({
      code: Code.Photo.TooLarge,
      field: 'photo',
      params: { max_mb: 5 },
    });
    expect(out).toContain('5 mb');
  });

  it('names the question for an invalid rsvp answer format', () => {
    expect(
      messageForCode({
        code: Code.Event.RsvpAnswerInvalidFormat,
        field: 'answers',
        params: { label: 'dietary needs' },
      }),
    ).toBe('invalid answer format for "dietary needs"');
    expect(messageForCode({ code: Code.Event.RsvpAnswerInvalidFormat, field: 'answers' })).toBe(
      'invalid answer format',
    );
  });

  it('explains speech template errors', () => {
    expect(messageForCode({ code: Code.SpeechTemplate.InvalidDoc, field: 'walk_pm' })).toBe(
      'that speech section is not valid',
    );
    expect(
      messageForCode({
        code: Code.SpeechTemplate.TooManyRoles,
        field: 'open_roles',
        params: { max: 20 },
      }),
    ).toBe('at most 20 open roles');
    expect(messageForCode({ code: Code.SpeechTemplate.TooManyRoles, field: 'open_roles' })).toBe(
      'too many open roles',
    );
    expect(
      messageForCode({
        code: Code.SpeechTemplate.RoleTooLong,
        field: 'open_roles',
        params: { max: 200 },
      }),
    ).toBe('each role must be at most 200 characters');
    expect(messageForCode({ code: Code.SpeechTemplate.RoleTooLong, field: 'open_roles' })).toBe(
      'a role is too long',
    );
  });

  it('says a speech blank is not valid', () => {
    expect(messageForCode({ code: Code.Speech.InvalidValues, field: 'values' })).toBe(
      'one of the speech blanks is not valid',
    );
  });

  it('asks for the event format before saving a speech', () => {
    expect(messageForCode({ code: Code.Speech.FormatRequired, field: 'event_format' })).toBe(
      'pick walk or restaurant first',
    );
  });

  it('explains welcome back email errors', () => {
    expect(messageForCode({ code: Code.MemberRestoredEmail.BodyRequired, field: 'body' })).toBe(
      'welcome back email body is required',
    );
    expect(
      messageForCode({
        code: Code.MemberRestoredEmail.BodyTooLong,
        field: 'body',
        params: { max_length: 5000 },
      }),
    ).toBe('welcome back email must be at most 5000 characters');
    expect(messageForCode({ code: Code.MemberRestoredEmail.BodyTooLong, field: 'body' })).toBe(
      'welcome back email is too long',
    );
  });

  it('says a tentative request is archived, not rejected', () => {
    expect(
      messageForCode({ code: Code.JoinRequest.TentativeCannotBeRejected, field: null }),
    ).toMatch(/archive them from the members screen/);
  });

  it('points to the existing open join request', () => {
    expect(
      messageForCode({ code: Code.JoinRequest.OpenRequestExists, field: 'phone_number' }),
    ).toBe('this number already has an open request — review that one instead');
  });

  it('returns a safe fallback for unknown codes', () => {
    expect(messageForCode({ code: 'something_the_fe_doesnt_know', field: null })).toMatch(
      /double-check/i,
    );
  });
});

describe('messagesFromFieldErrors', () => {
  it('joins multiple distinct errors with a middle dot', () => {
    const errors: FieldError[] = [
      { code: Code.Generic.FieldRequired, field: 'title' },
      { code: Code.Event.StartDatetimeRequiredUnlessTbd, field: 'start_datetime' },
    ];
    const out = messagesFromFieldErrors(errors);
    expect(out).toContain('title');
    expect(out).toContain('start time');
    expect(out).toContain(' · ');
  });

  it('deduplicates repeated messages', () => {
    const errors: FieldError[] = [
      { code: Code.Url.Invalid, field: 'whatsapp_link' },
      { code: Code.Url.Invalid, field: 'whatsapp_link' },
    ];
    const out = messagesFromFieldErrors(errors);
    expect(out).toBe('enter a valid url');
  });
});
