import { describe, it, expect } from 'vitest';
import { extractApiError, extractApiErrorOr } from './apiErrors';
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
