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
