// Unit tests for the refresh-lock interceptor.
// We mock axios at the network layer and exercise the state machine:
//   - 401 triggers a single in-flight refresh even under concurrent requests
//   - successful refresh retries the original request with the new token
//   - failed refresh fires onSessionExpired and rethrows
//   - retried requests aren't retried again (no infinite loop)

import { describe, it, expect, beforeEach, vi } from 'vitest';
import MockAdapter from 'axios-mock-adapter';
import { apiClient, authClient, setAuthBridge } from './client';

let accessToken: string | null = null;
const onSessionExpired = vi.fn();

beforeEach(() => {
  accessToken = 'access-v1';
  onSessionExpired.mockReset();
  setAuthBridge({
    getAccessToken: () => accessToken,
    setAccessToken: (t) => {
      accessToken = t;
    },
    onSessionExpired,
  });
});

describe('apiClient refresh interceptor', () => {
  it('attaches Bearer access token to requests', async () => {
    const mock = new MockAdapter(apiClient);
    mock.onGet('/api/ping').reply((config) => {
      expect(config.headers?.Authorization).toBe('Bearer access-v1');
      return [200, { ok: true }];
    });
    await apiClient.get('/api/ping');
    mock.restore();
  });

  it('refreshes once and retries on a 401, even under concurrent requests', async () => {
    const apiMock = new MockAdapter(apiClient);
    const authMock = new MockAdapter(authClient);

    let refreshCalls = 0;
    authMock.onPost('/api/auth/refresh/').reply(() => {
      refreshCalls += 1;
      return [200, { access: 'access-v2' }];
    });

    let firstAttemptCount = 0;
    apiMock.onGet('/api/events').reply((config) => {
      const auth = (config.headers as Record<string, string> | undefined)?.Authorization;
      if (auth === 'Bearer access-v1') {
        firstAttemptCount += 1;
        return [401, { detail: 'expired' }];
      }
      return [200, { items: [] }];
    });

    const [r1, r2] = await Promise.all([
      apiClient.get('/api/events'),
      apiClient.get('/api/events'),
    ]);
    expect(r1.status).toBe(200);
    expect(r2.status).toBe(200);
    // Both requests got a 401 on first try.
    expect(firstAttemptCount).toBe(2);
    // But only ONE refresh call — the lock worked.
    expect(refreshCalls).toBe(1);
    expect(accessToken).toBe('access-v2');

    apiMock.restore();
    authMock.restore();
  });

  it('calls onSessionExpired when refresh itself fails', async () => {
    const apiMock = new MockAdapter(apiClient);
    const authMock = new MockAdapter(authClient);

    apiMock.onGet('/api/events').reply(401, { detail: 'expired' });
    authMock.onPost('/api/auth/refresh/').reply(401, { detail: 'gone' });

    await expect(apiClient.get('/api/events')).rejects.toThrow();
    expect(onSessionExpired).toHaveBeenCalledOnce();

    apiMock.restore();
    authMock.restore();
  });

  it('replays a mutating request once after a clean 401 + successful refresh', async () => {
    // A clean 401 means the server rejected the request before processing it
    // (expired access token), so it never mutated state — replaying it with the
    // refreshed token is safe and recovers the action instead of failing it.
    const apiMock = new MockAdapter(apiClient);
    const authMock = new MockAdapter(authClient);
    authMock.onPost('/api/auth/refresh/').reply(200, { access: 'access-v2' });

    let postAttempts = 0;
    apiMock.onPost('/api/community/events/').reply((config) => {
      postAttempts += 1;
      const auth = (config.headers as Record<string, string> | undefined)?.Authorization;
      if (auth === 'Bearer access-v1') {
        return [401, { detail: 'expired' }];
      }
      return [201, { id: 'evt-1' }];
    });

    const res = await apiClient.post('/api/community/events/', { title: 'x' });
    // Succeeded on the replay with the refreshed token.
    expect(res.status).toBe(201);
    // Sent exactly twice: original (401) + one replay. Never more.
    expect(postAttempts).toBe(2);
    // Session was always valid, so we must NOT force logout.
    expect(onSessionExpired).not.toHaveBeenCalled();
    expect(accessToken).toBe('access-v2');

    apiMock.restore();
    authMock.restore();
  });

  it('does not replay a mutation more than once if it still 401s after refresh', async () => {
    const apiMock = new MockAdapter(apiClient);
    const authMock = new MockAdapter(authClient);
    authMock.onPost('/api/auth/refresh/').reply(200, { access: 'access-v2' });

    let postAttempts = 0;
    apiMock.onPost('/api/community/events/').reply(() => {
      postAttempts += 1;
      return [401, { detail: 'still expired' }];
    });

    await expect(apiClient.post('/api/community/events/', { title: 'x' })).rejects.toThrow();
    // Exactly two sends: original + one replay. No infinite loop, no triple-submit.
    expect(postAttempts).toBe(2);
    expect(onSessionExpired).not.toHaveBeenCalled();

    apiMock.restore();
    authMock.restore();
  });

  it('does not force logout when refresh fails transiently (5xx)', async () => {
    const apiMock = new MockAdapter(apiClient);
    const authMock = new MockAdapter(authClient);
    apiMock.onGet('/api/events').reply(401, { detail: 'expired' });
    // Refresh endpoint is briefly down — NOT a real 401.
    authMock.onPost('/api/auth/refresh/').reply(503, { detail: 'unavailable' });

    await expect(apiClient.get('/api/events')).rejects.toThrow();
    // Transient failure: session is NOT nuked.
    expect(onSessionExpired).not.toHaveBeenCalled();

    apiMock.restore();
    authMock.restore();
  });

  it('does not force logout when refresh fails with a network error', async () => {
    const apiMock = new MockAdapter(apiClient);
    const authMock = new MockAdapter(authClient);
    apiMock.onGet('/api/events').reply(401, { detail: 'expired' });
    authMock.onPost('/api/auth/refresh/').networkError();

    await expect(apiClient.get('/api/events')).rejects.toThrow();
    expect(onSessionExpired).not.toHaveBeenCalled();

    apiMock.restore();
    authMock.restore();
  });

  it('does not retry a second time after a successful refresh still fails', async () => {
    const apiMock = new MockAdapter(apiClient);
    const authMock = new MockAdapter(authClient);
    authMock.onPost('/api/auth/refresh/').reply(200, { access: 'access-v2' });
    // The retried request still 401s (e.g., permission revoked server-side).
    let attempts = 0;
    apiMock.onGet('/api/events').reply(() => {
      attempts += 1;
      return [401, { detail: 'still expired' }];
    });

    await expect(apiClient.get('/api/events')).rejects.toThrow();
    // Should have attempted exactly twice: original + one retry. No infinite loop.
    expect(attempts).toBe(2);

    apiMock.restore();
    authMock.restore();
  });
});
