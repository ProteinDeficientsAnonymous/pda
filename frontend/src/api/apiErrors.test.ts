import { describe, it, expect } from 'vitest';
import { extractApiError, extractApiErrorOr, getApiStatus, hasErrorCode } from './apiErrors';
import { Code } from './validationCodes';

function axiosError(status: number, data: unknown) {
  return Object.assign(new Error(String(status)), {
    isAxiosError: true,
    response: { status, data },
  });
}

describe('extractApiError', () => {
  it('returns null for non-axios errors', () => {
    expect(extractApiError(new Error('boom'))).toBeNull();
    expect(extractApiError('string')).toBeNull();
    expect(extractApiError(undefined)).toBeNull();
  });

  it('returns null when response data is missing', () => {
    expect(extractApiError(axiosError(500, undefined))).toBeNull();
  });

  it('passes through legacy string detail', () => {
    expect(extractApiError(axiosError(400, { detail: 'just a string' }))).toBe('just a string');
  });

  it('maps a single validation code to its message', () => {
    expect(
      extractApiError(
        axiosError(401, { detail: [{ code: Code.Auth.InvalidCredentials, field: null }] }),
      ),
    ).toContain("phone number and password don't match");
  });

  it('renders generic field_required with the field name', () => {
    expect(
      extractApiError(axiosError(422, { detail: [{ code: 'field_required', field: 'title' }] })),
    ).toContain('title');
  });

  it('joins multiple distinct codes with a middle dot', () => {
    const out = extractApiError(
      axiosError(422, {
        detail: [
          { code: 'field_required', field: 'title' },
          { code: Code.Url.Invalid, field: 'whatsapp_link' },
        ],
      }),
    );
    expect(out).toContain('title');
    expect(out).toContain('valid url');
    expect(out).toContain(' · ');
  });

  it('falls back to a safe message for unknown codes', () => {
    expect(
      extractApiError(axiosError(422, { detail: [{ code: 'something.unknown', field: null }] })),
    ).toMatch(/double-check/i);
  });
});

describe('extractApiErrorOr', () => {
  it('returns the extracted message when one is recoverable', () => {
    expect(
      extractApiErrorOr(
        axiosError(401, { detail: [{ code: Code.Auth.InvalidCredentials, field: null }] }),
        'fallback',
      ),
    ).toContain("phone number and password don't match");
  });

  it('returns the fallback when no message is recoverable', () => {
    expect(extractApiErrorOr(new Error('not an axios error'), 'fallback')).toBe('fallback');
    expect(extractApiErrorOr(axiosError(500, undefined), 'fallback')).toBe('fallback');
  });
});

describe('getApiStatus', () => {
  it('returns the status when the error is an axios error with a response', () => {
    expect(getApiStatus(axiosError(403, { detail: 'nope' }))).toBe(403);
    expect(getApiStatus(axiosError(429, undefined))).toBe(429);
  });

  it('returns null for non-axios errors', () => {
    expect(getApiStatus(new Error('boom'))).toBeNull();
    expect(getApiStatus('string')).toBeNull();
    expect(getApiStatus(undefined)).toBeNull();
  });

  it('returns null for axios errors with no response (e.g. network)', () => {
    const networkErr = Object.assign(new Error('network'), { isAxiosError: true });
    expect(getApiStatus(networkErr)).toBeNull();
  });
});

describe('hasErrorCode', () => {
  it('returns true when the structured detail contains the code', () => {
    const err = axiosError(409, {
      detail: [{ code: Code.Event.FlagAlreadyFlagged, field: null }],
    });
    expect(hasErrorCode(err, Code.Event.FlagAlreadyFlagged)).toBe(true);
  });

  it('returns true when the code is one of several entries', () => {
    const err = axiosError(422, {
      detail: [
        { code: 'field_required', field: 'title' },
        { code: Code.CoHostInvite.NotPending, field: null },
      ],
    });
    expect(hasErrorCode(err, Code.CoHostInvite.NotPending)).toBe(true);
  });

  it('returns false when the code is not present', () => {
    const err = axiosError(409, { detail: [{ code: 'something.else', field: null }] });
    expect(hasErrorCode(err, Code.Event.FlagAlreadyFlagged)).toBe(false);
  });

  it('returns false for legacy string-detail responses', () => {
    expect(hasErrorCode(axiosError(400, { detail: 'free text' }), 'anything')).toBe(false);
  });

  it('returns false for non-axios errors', () => {
    expect(hasErrorCode(new Error('boom'), 'anything')).toBe(false);
  });
});
