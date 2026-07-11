import { getApiStatus } from '@/api/apiErrors';

export const MAX_BACKOFF_MS = 30_000;
export const RATE_LIMIT_BACKOFF_MIN_MS = 30_000;
export const RATE_LIMIT_BACKOFF_JITTER_MS = 30_000;

export function normalBackoffDelay(retry: number): number {
  return Math.min(2 ** (retry - 1) * 1000, MAX_BACKOFF_MS);
}

export function rateLimitBackoffDelay(rand: number = Math.random()): number {
  return RATE_LIMIT_BACKOFF_MIN_MS + Math.floor(rand * RATE_LIMIT_BACKOFF_JITTER_MS);
}

export function isRateLimitError(err: unknown): boolean {
  return getApiStatus(err) === 429;
}
