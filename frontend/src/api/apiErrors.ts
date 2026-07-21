import { isAxiosError } from 'axios';

import { type FieldError, messagesFromFieldErrors } from './validationCodes';

/**
 * Extract a user-facing message from any API error.
 * Returns null when the error isn't an axios error we can interpret — callers
 * fall back to their own default ("couldn't save — try again", etc.).
 */
export function extractApiError(err: unknown): string | null {
  if (!isAxiosError(err)) return null;
  const data = err.response?.data as Record<string, unknown> | undefined;
  if (!data) return null;

  // Legacy shape: { detail: "string" }
  if (typeof data.detail === 'string' && data.detail) return data.detail;

  // Structured shape: { detail: [{ code, field, params? }, ...] }
  if (Array.isArray(data.detail)) {
    const fieldErrors = data.detail.filter(
      (e): e is FieldError =>
        typeof e === 'object' && e !== null && typeof (e as FieldError).code === 'string',
    );
    if (fieldErrors.length > 0) return messagesFromFieldErrors(fieldErrors);
  }

  return null;
}

/**
 * Like extractApiError but returns a fallback string when no message is
 * recoverable. Convenience for call sites that always want a display string.
 */
export function extractApiErrorOr(err: unknown, fallback: string): string {
  return extractApiError(err) ?? fallback;
}

/**
 * HTTP status from any API error, or null if the error isn't an axios error
 * with a response. Use this instead of importing `isAxiosError` directly so
 * call sites don't reach into `error.response?.status` on their own.
 */
export function getApiStatus(err: unknown): number | null {
  if (!isAxiosError(err)) return null;
  return err.response?.status ?? null;
}

/**
 * True if the error carries a structured-detail entry with the given code.
 * Prefer this over status-based branching when the code is more specific than
 * the status (e.g. distinguishing flag_already_flagged from any 409).
 */
export function hasErrorCode(err: unknown, code: string): boolean {
  return getErrorParams(err, code) !== null;
}

/**
 * The `params` of the structured-detail entry matching `code`, or null if the
 * error doesn't carry that code. Use alongside hasErrorCode when the caller
 * needs the params payload (e.g. a count), not just a yes/no check.
 */
export function getErrorParams(err: unknown, code: string): Record<string, unknown> | null {
  if (!isAxiosError(err)) return null;
  const data = err.response?.data as Record<string, unknown> | undefined;
  if (!data || !Array.isArray(data.detail)) return null;
  const match = data.detail.find(
    (e): e is FieldError => typeof e === 'object' && e !== null && (e as FieldError).code === code,
  );
  return match ? (match.params ?? {}) : null;
}
