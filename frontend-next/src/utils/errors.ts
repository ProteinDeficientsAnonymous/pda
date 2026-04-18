import { isAxiosError } from 'axios';

export function extractApiError(err: unknown, fallback: string): string {
  if (isAxiosError(err)) {
    const status = err.response?.status;
    if (status === 401) return 'invalid phone or password';
    const data = err.response?.data as { detail?: unknown } | undefined;
    if (typeof data?.detail === 'string') return data.detail;
  }
  return fallback;
}
