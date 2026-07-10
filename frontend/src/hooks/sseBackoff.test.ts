import { AxiosError, AxiosHeaders } from 'axios';
import { describe, expect, it } from 'vitest';

import {
  isRateLimitError,
  MAX_BACKOFF_MS,
  normalBackoffDelay,
  RATE_LIMIT_BACKOFF_MIN_MS,
  rateLimitBackoffDelay,
} from './sseBackoff';

function axiosErrorWithStatus(status: number): AxiosError {
  const err = new AxiosError('err');
  err.response = {
    status,
    data: {},
    statusText: '',
    headers: {},
    config: { headers: new AxiosHeaders() },
  };
  return err;
}

describe('normalBackoffDelay', () => {
  it('grows exponentially from 1s and caps at MAX_BACKOFF_MS', () => {
    expect(normalBackoffDelay(1)).toBe(1000);
    expect(normalBackoffDelay(2)).toBe(2000);
    expect(normalBackoffDelay(3)).toBe(4000);
    expect(normalBackoffDelay(10)).toBe(MAX_BACKOFF_MS);
  });
});

describe('rateLimitBackoffDelay', () => {
  it('always waits at least a full rate-limit window, far above the fast backoff', () => {
    expect(rateLimitBackoffDelay(0)).toBe(RATE_LIMIT_BACKOFF_MIN_MS);
    expect(rateLimitBackoffDelay(0)).toBeGreaterThan(normalBackoffDelay(1));
    // Even the earliest fast-backoff cap stays at/under the rate-limit floor.
    expect(rateLimitBackoffDelay(0)).toBeGreaterThanOrEqual(MAX_BACKOFF_MS);
  });

  it('jitters upward so multiple tabs do not wake in lockstep', () => {
    expect(rateLimitBackoffDelay(0.999)).toBeGreaterThan(RATE_LIMIT_BACKOFF_MIN_MS);
  });
});

describe('isRateLimitError', () => {
  it('is true only for a 429 axios error', () => {
    expect(isRateLimitError(axiosErrorWithStatus(429))).toBe(true);
    expect(isRateLimitError(axiosErrorWithStatus(500))).toBe(false);
    expect(isRateLimitError(axiosErrorWithStatus(401))).toBe(false);
    expect(isRateLimitError(new Error('network down'))).toBe(false);
    expect(isRateLimitError(null)).toBe(false);
  });
});
