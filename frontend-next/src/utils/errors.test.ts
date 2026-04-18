import { describe, it, expect } from 'vitest';
import { extractApiError } from './errors';

describe('extractApiError', () => {
  it('returns invalidCredentials for 401', () => {
    const error = Object.assign(new Error('401'), {
      isAxiosError: true,
      response: { status: 401, data: { detail: 'Invalid credentials' } },
    });
    expect(extractApiError(error, 'fallback')).toBe('invalid phone or password');
  });

  it('returns validationError with detail for 400', () => {
    const error = Object.assign(new Error('400'), {
      isAxiosError: true,
      response: { status: 400, data: { detail: 'Name, email required' } },
    });
    expect(extractApiError(error, 'fallback')).toBe('Name, email required');
  });

  it('returns validationError with detail for 422', () => {
    const error = Object.assign(new Error('422'), {
      isAxiosError: true,
      response: { status: 422, data: { detail: 'Validation failed' } },
    });
    expect(extractApiError(error, 'fallback')).toBe('Validation failed');
  });

  it('returns serverError for 500', () => {
    const error = Object.assign(new Error('500'), {
      isAxiosError: true,
      response: { status: 500 },
    });
    expect(extractApiError(error, 'fallback')).toBe('fallback');
  });

  it('returns networkError for connectionError', () => {
    const error = Object.assign(new Error('connection'), {
      isAxiosError: true,
      response: undefined,
    });
    expect(extractApiError(error, 'fallback')).toBe('fallback');
  });

  it('returns fallback for non-Axios error', () => {
    const error = new Error('something unexpected');
    expect(extractApiError(error, 'fallback')).toBe('fallback');
  });

  it('returns fallback when detail is missing', () => {
    const error = Object.assign(new Error('400'), {
      isAxiosError: true,
      response: { status: 400, data: 'not a map' },
    });
    expect(extractApiError(error, 'fallback')).toBe('fallback');
  });
});