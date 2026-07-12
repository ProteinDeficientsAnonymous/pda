import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { User } from '@/models/user';

import MagicLoginScreen from './MagicLoginScreen';

// MagicLoginScreen calls the store's magicLogin action, then reads
// useAuthStore.getState().user to decide where to navigate. We mock the store so
// the action populates a controllable user and getState() returns it.
let currentUser: User | null = null;
const magicLoginMock = vi.fn(async () => {
  // user is seeded per-test before the screen mounts
});

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 'u1',
    phoneNumber: '+12125550001',
    firstName: 'Alice',
    lastName: '',
    fullName: 'Alice',
    nickname: '',
    email: 'alice@example.com',
    bio: '',
    pronouns: '',
    isSuperuser: false,
    isStaff: false,
    needsOnboarding: false,
    needsPasswordReset: false,
    needsGuidelinesConsent: false,
    needsSmsConsent: false,
    showPhone: false,
    showEmail: false,
    weekStart: 'sunday',
    calendarFeedScope: 'all',
    profilePhotoUrl: '',
    photoUpdatedAt: null,
    roles: [],
    ...overrides,
  };
}

vi.mock('@/auth/store', () => ({
  useAuthStore: Object.assign(
    (selector: (s: { magicLogin: typeof magicLoginMock }) => unknown) =>
      selector({ magicLogin: magicLoginMock }),
    { getState: () => ({ user: currentUser }) },
  ),
}));

function renderAt(token: string) {
  return render(
    <MemoryRouter initialEntries={[`/magic-login/${token}`]}>
      <Routes>
        <Route path="/magic-login/:token" element={<MagicLoginScreen />} />
        <Route path="/new-password" element={<div>new password page</div>} />
        <Route path="/onboarding" element={<div>onboarding page</div>} />
        <Route path="/consent" element={<div>consent page</div>} />
        <Route path="/calendar" element={<div>calendar page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('MagicLoginScreen', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentUser = null;
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
});
