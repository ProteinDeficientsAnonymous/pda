import { apiClient } from '@/api/client';
import { useAuthStore } from '@/auth/store';

const ERROR_REPORT_PATH = '/api/community/error-report/';
const CONTEXT_MAX_LENGTH = 500;

interface NormalizedError {
  message: string;
  stack: string;
}

function normalizeError(error: unknown): NormalizedError {
  if (error instanceof Error) {
    return { message: error.message || String(error), stack: error.stack ?? '' };
  }
  if (typeof error === 'string') {
    return { message: error, stack: '' };
  }
  try {
    return { message: JSON.stringify(error), stack: '' };
  } catch {
    return { message: String(error), stack: '' };
  }
}

function serializeContext(context: Record<string, unknown> | undefined): string {
  if (!context) return '';
  try {
    const json = JSON.stringify(context);
    return json.length > CONTEXT_MAX_LENGTH ? json.slice(0, CONTEXT_MAX_LENGTH) : json;
  } catch {
    return '';
  }
}

export async function reportError(
  error: unknown,
  route: string,
  context?: Record<string, unknown>,
): Promise<void> {
  const { accessToken } = useAuthStore.getState();
  if (!accessToken) {
    console.error(error);
    return;
  }

  const { message, stack } = normalizeError(error);
  const userAgent = typeof navigator !== 'undefined' ? navigator.userAgent : '';
  try {
    await apiClient.post(ERROR_REPORT_PATH, {
      error: message,
      stack_trace: stack,
      route,
      user_agent: userAgent,
      context: serializeContext(context),
      client_timestamp: new Date().toISOString(),
    });
  } catch {
    // Never re-throw from the reporter — surface locally instead.
    console.error(error);
  }
}
