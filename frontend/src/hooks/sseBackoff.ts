import { isAxiosError } from 'axios';

export const MAX_BACKOFF_MS = 30_000;
// The sse-ticket endpoint is rate-limited per-user (30/m). With several tabs
// open, a backend blip makes every tab re-mint on each backoff step and can
// trip that shared limit — locking the user out of live notifications while
// they keep retrying blindly. On a 429 the window is measured in minutes, so
// retrying in 1s is pointless: wait out roughly a full window, jittered so
// multiple tabs don't all wake and re-mint in lockstep.
export const RATE_LIMIT_BACKOFF_MIN_MS = 30_000;
export const RATE_LIMIT_BACKOFF_JITTER_MS = 30_000;

/** Exponential backoff for the nth (1-based) reconnect attempt, capped. */
export function normalBackoffDelay(retry: number): number {
  return Math.min(2 ** (retry - 1) * 1000, MAX_BACKOFF_MS);
}

/** Long, jittered backoff for a rate-limited (429) ticket mint. */
export function rateLimitBackoffDelay(rand: number = Math.random()): number {
  return RATE_LIMIT_BACKOFF_MIN_MS + Math.floor(rand * RATE_LIMIT_BACKOFF_JITTER_MS);
}

export function isRateLimitError(err: unknown): boolean {
  return isAxiosError(err) && err.response?.status === 429;
}
