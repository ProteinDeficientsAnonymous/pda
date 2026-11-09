import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Code } from '@/api/validationCodes.gen';
import type { User } from '@/models/user';
import { apiError } from '@/test/apiError';
import { makeUser as makeSharedUser } from '@/test/fixtures';

import MagicLoginScreen from './MagicLoginScreen';

// MagicLoginScreen calls the store's magicLogin action, then reads
// useAuthStore.getState().user to decide where to navigate. We mock the store so
// the action populates a controllable user and getState() returns it.
let currentUser: User | null = null;
const magicLoginMock = vi.fn(async () => {
  // user is seeded per-test before the screen mounts
});

function makeUser(overrides: Partial<User> = {}): User {
  return makeSharedUser({
    id: 'u1',
    firstName: 'Alice',
    lastName: '',
    fullName: 'Alice',
    email: 'alice@example.com',
    ...overrides,
  });
}

vi.mock('@/auth/store', () => ({
  useAuthStore: Object.assign(
    (selector: (s: { magicLogin: typeof magicLoginMock }) => unknown) =>
      selector({ magicLogin: magicLoginMock }),
    { getState: () => ({ user: currentUser }) },
  ),
}));

function renderAt(token: string, redirect?: string) {
  const query = redirect === undefined ? '' : `?redirect=${encodeURIComponent(redirect)}`;
  return render(
    <MemoryRouter initialEntries={[`/magic-login/${token}${query}`]}>
      <Routes>
        <Route path="/magic-login/:token" element={<MagicLoginScreen />} />
        <Route path="/new-password" element={<div>new password page</div>} />
        <Route path="/onboarding" element={<div>onboarding page</div>} />
        <Route path="/consent" element={<div>consent page</div>} />
        <Route path="/calendar" element={<div>calendar page</div>} />
        <Route path="/events/:slug" element={<div>event page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('MagicLoginScreen', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentUser = null;
  });

  it('offers a rejected applicant the join form instead of a new link', async () => {
    magicLoginMock.mockRejectedValueOnce(apiError(403, Code.Auth.AccountRejected));
    renderAt('tok-rejected');
    expect(await screen.findByText(/request to join again/i)).toHaveAttribute('href', '/join');
    expect(screen.queryByText(/send me a new link/i)).toBeNull();
  });

  it('routes a needsPasswordReset user (has a name) to /new-password', async () => {
    currentUser = makeUser({ needsPasswordReset: true, firstName: 'Alice', fullName: 'Alice' });
    renderAt('tok-1');
    expect(await screen.findByText('new password page')).toBeInTheDocument();
  });

  it('routes a needsPasswordReset user with NO email to /onboarding (matches the gate)', async () => {
    // Regression: MagicLoginScreen used to send any named user to /new-password,
    // which the gate then bounced to /onboarding. Both must now agree.
    currentUser = makeUser({
      needsPasswordReset: true,
      firstName: 'Alice',
      fullName: 'Alice',
      email: '',
    });
    renderAt('tok-noemail');
    expect(await screen.findByText('onboarding page')).toBeInTheDocument();
  });

  it('routes a needsGuidelinesConsent user to /consent', async () => {
    currentUser = makeUser({ needsGuidelinesConsent: true });
    renderAt('tok-consent');
    expect(await screen.findByText('consent page')).toBeInTheDocument();
  });

  it('routes password setup before consent when both are pending', async () => {
    currentUser = makeUser({
      needsOnboarding: true,
      firstName: '',
      fullName: '',
      needsGuidelinesConsent: true,
    });
    renderAt('tok-both');
    expect(await screen.findByText('onboarding page')).toBeInTheDocument();
  });

  it('routes a plain login (no flags) to /calendar', async () => {
    currentUser = makeUser({ needsPasswordReset: false, needsOnboarding: false });
    renderAt('tok-2');
    expect(await screen.findByText('calendar page')).toBeInTheDocument();
  });

  it('routes a first-time user (needsOnboarding, empty name) to /onboarding', async () => {
    currentUser = makeUser({ needsOnboarding: true, firstName: '', fullName: '' });
    renderAt('tok-3');
    expect(await screen.findByText('onboarding page')).toBeInTheDocument();
  });

  it('consumes the token via the store magicLogin action', async () => {
    currentUser = makeUser();
    renderAt('tok-4');
    await waitFor(() => {
      expect(magicLoginMock).toHaveBeenCalledWith('tok-4');
    });
  });

  it('should land on /calendar when redirect is scheme-relative', async () => {
    currentUser = makeUser();
    renderAt('tok-evil', '//evil.example/phish');
    expect(await screen.findByText('calendar page')).toBeInTheDocument();
  });

  it('should tell a paused user they cannot sign in', async () => {
    magicLoginMock.mockRejectedValueOnce(apiError(403, Code.Auth.AccountPaused));
    renderAt('tok-paused');
    expect(await screen.findByText("can't sign in")).toBeInTheDocument();
    expect(
      screen.getByText("your membership is paused — you can't log in right now"),
    ).toBeInTheDocument();
  });

  it('should keep the cross-user message for other 403s', async () => {
    magicLoginMock.mockRejectedValueOnce(apiError(403));
    renderAt('tok-other');
    expect(await screen.findByText('already signed in')).toBeInTheDocument();
  });

  it('should follow a same-app redirect when login is complete', async () => {
    currentUser = makeUser();
    renderAt('tok-event', '/events/some-slug');
    expect(await screen.findByText('event page')).toBeInTheDocument();
  });

  it.each([
    ['onboarding', { needsOnboarding: true, firstName: '', fullName: '' }, 'onboarding page'],
    [
      'new-password',
      { needsPasswordReset: true, firstName: 'Alice', fullName: 'Alice' },
      'new password page',
    ],
    ['consent', { needsGuidelinesConsent: true }, 'consent page'],
  ] as const)(
    'should ignore redirect when post-auth sends the user to %s',
    async (name, overrides, page) => {
      currentUser = makeUser(overrides);
      renderAt(`tok-${name}`, '/events/some-slug');
      expect(await screen.findByText(page)).toBeInTheDocument();
    },
  );
});
