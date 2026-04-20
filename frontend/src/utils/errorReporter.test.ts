import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

import { apiClient } from '@/api/client';
import { useAuthStore } from '@/auth/store';
import { reportError } from './errorReporter';

const mockedPost = vi.mocked(apiClient.post);

const AUTHED_STATE = {
  status: 'authed' as const,
  user: null,
  accessToken: 'test-access-token',
};

const UNAUTHED_STATE = {
  status: 'unauthed' as const,
  user: null,
  accessToken: null,
};

const consoleErrorSpy = vi.spyOn(console, 'error');

beforeEach(() => {
  vi.clearAllMocks();
  consoleErrorSpy.mockImplementation(() => {});
});

afterEach(() => {
  consoleErrorSpy.mockReset();
  useAuthStore.setState(UNAUTHED_STATE);
});

describe('reportError', () => {
  it('POSTs error payload with token when authenticated', async () => {
    useAuthStore.setState(AUTHED_STATE);
    mockedPost.mockResolvedValueOnce({ data: { detail: 'Error report received.' } });

    const err = new Error('boom');
    await reportError(err, '/calendar');

    expect(mockedPost).toHaveBeenCalledTimes(1);
    const [path, body] = mockedPost.mock.calls[0] ?? [];
    expect(path).toBe('/api/community/error-report/');
    const payload = body as {
      error: string;
      stack_trace: string;
      route: string;
      client_timestamp: string;
    };
    expect(payload.error).toBe('boom');
    expect(payload.stack_trace).toEqual(expect.stringContaining('Error'));
    expect(consoleErrorSpy).not.toHaveBeenCalled();
  });

  it('always includes navigator.userAgent in the payload', async () => {
    useAuthStore.setState(AUTHED_STATE);
    Object.defineProperty(window.navigator, 'userAgent', {
      value: 'jsdom-error-reporter',
      configurable: true,
    });
    mockedPost.mockResolvedValueOnce({ data: { detail: 'ok' } });

    await reportError(new Error('boom'), '/calendar');

    const [, body] = mockedPost.mock.calls[0] ?? [];
    expect((body as { user_agent: string }).user_agent).toBe('jsdom-error-reporter');
  });

  it('serializes optional caller context as a JSON string', async () => {
    useAuthStore.setState(AUTHED_STATE);
    mockedPost.mockResolvedValueOnce({ data: { detail: 'ok' } });

    await reportError(new Error('boom'), '/calendar', { boundary: 'Root', extra: 1 });

    const [, body] = mockedPost.mock.calls[0] ?? [];
    expect((body as { context: string }).context).toBe(
      JSON.stringify({ boundary: 'Root', extra: 1 }),
    );
  });

  it('omits context when no caller context is supplied', async () => {
    useAuthStore.setState(AUTHED_STATE);
    mockedPost.mockResolvedValueOnce({ data: { detail: 'ok' } });

    await reportError(new Error('boom'), '/calendar');

    const [, body] = mockedPost.mock.calls[0] ?? [];
    expect((body as { context: string }).context).toBe('');
  });

  it('includes the current route in the payload', async () => {
    useAuthStore.setState(AUTHED_STATE);
    mockedPost.mockResolvedValueOnce({ data: { detail: 'ok' } });

    await reportError(new Error('nope'), '/events/42');

    const [, body] = mockedPost.mock.calls[0] ?? [];
    expect((body as { route: string }).route).toBe('/events/42');
    // client_timestamp is a valid ISO string
    const payload = body as { client_timestamp: string };
    expect(Number.isNaN(Date.parse(payload.client_timestamp))).toBe(false);
  });

  it('does not POST when no access token — falls back to console.error', async () => {
    useAuthStore.setState(UNAUTHED_STATE);

    const err = new Error('unauthed error');
    await reportError(err, '/login');

    expect(mockedPost).not.toHaveBeenCalled();
    expect(consoleErrorSpy).toHaveBeenCalledWith(err);
  });

  it('falls back to console.error when POST fails and never re-throws', async () => {
    useAuthStore.setState(AUTHED_STATE);
    const networkErr = new Error('network down');
    mockedPost.mockRejectedValueOnce(networkErr);

    const original = new Error('original error');
    await expect(reportError(original, '/calendar')).resolves.toBeUndefined();

    expect(mockedPost).toHaveBeenCalledTimes(1);
    expect(consoleErrorSpy).toHaveBeenCalledWith(original);
  });
});
