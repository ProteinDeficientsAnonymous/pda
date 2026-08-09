import MockAdapter from 'axios-mock-adapter';
import { beforeEach, describe, expect, it } from 'vitest';

import { authClient } from './client';

import { restoreSession } from './auth';

const wireUser = {
  id: 'user-1',
  phone_number: '+12125551234',
  full_name: 'Alice',
  needs_onboarding: false,
  roles: [],
};

describe('restoreSession', () => {
  let authMock: MockAdapter;

  beforeEach(() => {
    authMock = new MockAdapter(authClient);
  });

  it('returns the session on a successful refresh', async () => {
    authMock.onPost('/api/auth/refresh/').reply(200, { access: 'tok-1' });
    authMock.onGet('/api/auth/me/').reply(200, wireUser);

    const result = await restoreSession();

    expect(result?.access).toBe('tok-1');
    expect(result?.user.id).toBe('user-1');
  });

  it('returns null immediately on a real 401 without retrying', async () => {
    let calls = 0;
    authMock.onPost('/api/auth/refresh/').reply(() => {
      calls += 1;
      return [401, { detail: 'invalid' }];
    });

    const result = await restoreSession();

    expect(result).toBeNull();
    expect(calls).toBe(1);
  });

  it('retries once and succeeds after a transient failure', async () => {
    let calls = 0;
    authMock.onPost('/api/auth/refresh/').reply(() => {
      calls += 1;
      if (calls === 1) return [500, { detail: 'server error' }];
      return [200, { access: 'tok-2' }];
    });
    authMock.onGet('/api/auth/me/').reply(200, wireUser);

    const result = await restoreSession();

    expect(calls).toBe(2);
    expect(result?.access).toBe('tok-2');
  });

  it('gives up and returns null after two transient failures', async () => {
    let calls = 0;
    authMock.onPost('/api/auth/refresh/').reply(() => {
      calls += 1;
      return [500, { detail: 'server error' }];
    });

    const result = await restoreSession();

    expect(calls).toBe(2);
    expect(result).toBeNull();
  });
});
