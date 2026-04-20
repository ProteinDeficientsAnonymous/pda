import { isAxiosError } from 'axios';

interface NinjaValidationError {
  msg?: string;
  loc?: (string | number)[];
}

function formatValidationErrors(items: NinjaValidationError[]): string | null {
  const msgs = items
    .map((item) => (typeof item.msg === 'string' ? item.msg.toLowerCase() : null))
    .filter((m): m is string => Boolean(m));
  if (msgs.length === 0) return null;
  return msgs.join(' · ');
}

export function extractApiError(err: unknown, fallback: string): string {
  if (isAxiosError(err)) {
    const status = err.response?.status;
    if (status === 401) return 'invalid phone or password';
    const data = err.response?.data as { detail?: unknown } | undefined;
    if (typeof data?.detail === 'string') return data.detail;
    if (Array.isArray(data?.detail)) {
      const formatted = formatValidationErrors(data.detail as NinjaValidationError[]);
      if (formatted) return formatted;
    }
  }
  return fallback;
}
