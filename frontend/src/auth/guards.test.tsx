import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Permission } from '@/models/permissions';
import type { User } from '@/models/user';

import { EmailGate, OnboardingGate, RequireAuth, RequirePermission } from './guards';
import { useAuthStore } from './store';

// Prevent the store from wiring up real axios interceptors.
vi.mock('@/api/client', () => ({
  setAuthBridge: vi.fn(),
  authClient: { post: vi.fn(), get: vi.fn() },
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

// Prevent any real API calls from the store module.
vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  magicLogin: vi.fn(),
  restoreSession: vi.fn(),
  logout: vi.fn(),
  fetchMe: vi.fn(),
  completeOnboarding: vi.fn(),
  changePassword: vi.fn(),
  updateProfile: vi.fn(),
  uploadProfilePhoto: vi.fn(),
  deleteProfilePhoto: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 'user-1',
    phoneNumber: '+12125551234',
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
    hideLastName: false,
    weekStart: 'sunday',
    calendarFeedScope: 'all',
    profilePhotoUrl: '',
    photoUpdatedAt: null,
    roles: [],
    ...overrides,
  };
}

beforeEach(() => {
  useAuthStore.setState({
    status: 'unauthed',
    user: null,
    accessToken: null,
    profileStepActive: false,
  });
});

// ---------------------------------------------------------------------------
// RequireAuth
// ---------------------------------------------------------------------------

describe('RequireAuth', () => {
  it('redirects an unauthed user to /login with a redirect param', () => {
    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route element={<RequireAuth />}>
            <Route path="/protected" element={<div>protected content</div>} />
          </Route>
          <Route path="/login" element={<div>login page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('login page')).toBeInTheDocument();
    expect(screen.queryByText('protected content')).not.toBeInTheDocument();
  });

  it('renders the outlet for an authed user', () => {
    useAuthStore.setState({ status: 'authed', user: makeUser(), accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route element={<RequireAuth />}>
            <Route path="/protected" element={<div>protected content</div>} />
          </Route>
          <Route path="/login" element={<div>login page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('protected content')).toBeInTheDocument();
    expect(screen.queryByText('login page')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// RequirePermission
// ---------------------------------------------------------------------------

describe('RequirePermission', () => {
  it('redirects an unauthed user to /login with a redirect param', () => {
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route element={<RequirePermission perm={Permission.ManageUsers} />}>
            <Route path="/admin" element={<div>admin content</div>} />
          </Route>
          <Route path="/login" element={<div>login page</div>} />
          <Route path="/calendar" element={<div>calendar page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('login page')).toBeInTheDocument();
    expect(screen.queryByText('admin content')).not.toBeInTheDocument();
  });

  it('redirects an authed user without the required permission to /calendar', () => {
    useAuthStore.setState({ status: 'authed', user: makeUser(), accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route element={<RequirePermission perm={Permission.ManageUsers} />}>
            <Route path="/admin" element={<div>admin content</div>} />
          </Route>
          <Route path="/login" element={<div>login page</div>} />
          <Route path="/calendar" element={<div>calendar page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('calendar page')).toBeInTheDocument();
    expect(screen.queryByText('admin content')).not.toBeInTheDocument();
  });

  it('renders the outlet for an authed user with the required permission', () => {
    const user = makeUser({
      roles: [{ id: 'r1', name: 'mod', isDefault: true, permissions: [Permission.ManageUsers] }],
    });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route element={<RequirePermission perm={Permission.ManageUsers} />}>
            <Route path="/admin" element={<div>admin content</div>} />
          </Route>
          <Route path="/login" element={<div>login page</div>} />
          <Route path="/calendar" element={<div>calendar page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('admin content')).toBeInTheDocument();
    expect(screen.queryByText('calendar page')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// OnboardingGate
// ---------------------------------------------------------------------------

describe('OnboardingGate', () => {
  it('redirects a first-time user (needsOnboarding=true, empty name) to /onboarding', () => {
    const user = makeUser({ needsOnboarding: true, firstName: '', fullName: '' });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/calendar']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/calendar" element={<div>calendar page</div>} />
            <Route path="/onboarding" element={<div>onboarding page</div>} />
            <Route path="/new-password" element={<div>new password page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('onboarding page')).toBeInTheDocument();
    expect(screen.queryByText('calendar page')).not.toBeInTheDocument();
  });

  it('redirects a password-reset user (needsOnboarding=true, has name + email) to /new-password', () => {
    const user = makeUser({
      needsOnboarding: true,
      firstName: 'Alice',
      fullName: 'Alice',
      email: 'alice@example.com',
    });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/calendar']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/calendar" element={<div>calendar page</div>} />
            <Route path="/onboarding" element={<div>onboarding page</div>} />
            <Route path="/new-password" element={<div>new password page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('new password page')).toBeInTheDocument();
    expect(screen.queryByText('calendar page')).not.toBeInTheDocument();
  });

  it('redirects a legacy user (needsOnboarding=true, has a name but no email) to /onboarding', () => {
    // Pre-email-requirement users were approved with a name but never
    // supplied an email. On first login they must end up at /onboarding so
    // they can add one — /new-password has no email field and would loop.
    const user = makeUser({
      needsOnboarding: true,
      firstName: 'Alice',
      fullName: 'Alice',
      email: '',
    });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/calendar']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/calendar" element={<div>calendar page</div>} />
            <Route path="/onboarding" element={<div>onboarding page</div>} />
            <Route path="/new-password" element={<div>new password page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('onboarding page')).toBeInTheDocument();
    expect(screen.queryByText('new password page')).not.toBeInTheDocument();
  });

  it('redirects a needsPasswordReset user (has name + email) to /new-password', () => {
    const user = makeUser({
      needsOnboarding: false,
      needsPasswordReset: true,
      firstName: 'Bob',
      fullName: 'Bob',
      email: 'bob@example.com',
    });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/calendar']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/calendar" element={<div>calendar page</div>} />
            <Route path="/new-password" element={<div>new password page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('new password page')).toBeInTheDocument();
    expect(screen.queryByText('calendar page')).not.toBeInTheDocument();
  });

  it('does not bounce a needsPasswordReset user away from /new-password', () => {
    const user = makeUser({
      needsOnboarding: false,
      needsPasswordReset: true,
      firstName: 'Bob',
      fullName: 'Bob',
      email: 'bob@example.com',
    });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/new-password']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/new-password" element={<div>new password page</div>} />
            <Route path="/calendar" element={<div>calendar page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('new password page')).toBeInTheDocument();
    expect(screen.queryByText('calendar page')).not.toBeInTheDocument();
  });

  it('redirects a needsGuidelinesConsent user to /consent', () => {
    const user = makeUser({ needsGuidelinesConsent: true });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/calendar']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/calendar" element={<div>calendar page</div>} />
            <Route path="/consent" element={<div>consent page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('consent page')).toBeInTheDocument();
    expect(screen.queryByText('calendar page')).not.toBeInTheDocument();
  });

  it('does not bounce a needsGuidelinesConsent user away from /consent', () => {
    const user = makeUser({ needsGuidelinesConsent: true });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/consent']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/consent" element={<div>consent page</div>} />
            <Route path="/calendar" element={<div>calendar page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('consent page')).toBeInTheDocument();
    expect(screen.queryByText('calendar page')).not.toBeInTheDocument();
  });

  it('lets a needsGuidelinesConsent user read /guidelines (so consent is possible)', () => {
    const user = makeUser({ needsGuidelinesConsent: true });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/guidelines']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/guidelines" element={<div>guidelines page</div>} />
            <Route path="/consent" element={<div>consent page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('guidelines page')).toBeInTheDocument();
    expect(screen.queryByText('consent page')).not.toBeInTheDocument();
  });

  it('redirects an sms-only consent-pending user to /consent', () => {
    const user = makeUser({ needsGuidelinesConsent: false, needsSmsConsent: true });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/calendar']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/calendar" element={<div>calendar page</div>} />
            <Route path="/consent" element={<div>consent page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('consent page')).toBeInTheDocument();
    expect(screen.queryByText('calendar page')).not.toBeInTheDocument();
  });

  it('does not bounce an sms-only consent-pending user away from /consent', () => {
    const user = makeUser({ needsGuidelinesConsent: false, needsSmsConsent: true });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/consent']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/consent" element={<div>consent page</div>} />
            <Route path="/calendar" element={<div>calendar page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('consent page')).toBeInTheDocument();
    expect(screen.queryByText('calendar page')).not.toBeInTheDocument();
  });

  it('lets an sms-only consent-pending user read /sms-policy (so consent is possible)', () => {
    const user = makeUser({ needsGuidelinesConsent: false, needsSmsConsent: true });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/sms-policy']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/sms-policy" element={<div>sms policy page</div>} />
            <Route path="/consent" element={<div>consent page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('sms policy page')).toBeInTheDocument();
    expect(screen.queryByText('consent page')).not.toBeInTheDocument();
  });

  it('lets a guidelines-consent-pending user read /sms-policy too', () => {
    const user = makeUser({ needsGuidelinesConsent: true });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/sms-policy']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/sms-policy" element={<div>sms policy page</div>} />
            <Route path="/consent" element={<div>consent page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('sms policy page')).toBeInTheDocument();
    expect(screen.queryByText('consent page')).not.toBeInTheDocument();
  });

  it('sends a password setup to /onboarding before asking for consent', () => {
    // A brand-new user who owes both password setup and consent resolves the
    // password gate first — consent is only asked once setup is done.
    const user = makeUser({
      needsOnboarding: true,
      firstName: '',
      fullName: '',
      needsGuidelinesConsent: true,
    });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/calendar']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/calendar" element={<div>calendar page</div>} />
            <Route path="/onboarding" element={<div>onboarding page</div>} />
            <Route path="/consent" element={<div>consent page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('onboarding page')).toBeInTheDocument();
    expect(screen.queryByText('consent page')).not.toBeInTheDocument();
  });

  it('redirects a consented user on /consent to /calendar', () => {
    const user = makeUser({ needsGuidelinesConsent: false });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/consent']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/consent" element={<div>consent page</div>} />
            <Route path="/calendar" element={<div>calendar page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('calendar page')).toBeInTheDocument();
    expect(screen.queryByText('consent page')).not.toBeInTheDocument();
  });

  it('redirects an onboarding-complete user on /onboarding to /guidelines', () => {
    const user = makeUser({ needsOnboarding: false });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/onboarding']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/onboarding" element={<div>onboarding page</div>} />
            <Route path="/guidelines" element={<div>guidelines page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('guidelines page')).toBeInTheDocument();
    expect(screen.queryByText('onboarding page')).not.toBeInTheDocument();
  });

  it('keeps an onboarding-complete user on /onboarding while the profile step is active', () => {
    const user = makeUser({ needsOnboarding: false });
    useAuthStore.setState({
      status: 'authed',
      user,
      accessToken: 'tok-abc',
      profileStepActive: true,
    });

    render(
      <MemoryRouter initialEntries={['/onboarding']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/onboarding" element={<div>onboarding page</div>} />
            <Route path="/guidelines" element={<div>guidelines page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('onboarding page')).toBeInTheDocument();
    expect(screen.queryByText('guidelines page')).not.toBeInTheDocument();
  });

  it('redirects an onboarding-complete user on /login to /calendar', () => {
    const user = makeUser({ needsOnboarding: false });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route element={<OnboardingGate />}>
            <Route path="/login" element={<div>login page</div>} />
            <Route path="/calendar" element={<div>calendar page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('calendar page')).toBeInTheDocument();
    expect(screen.queryByText('login page')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// EmailGate
// ---------------------------------------------------------------------------

describe('EmailGate', () => {
  it('renders RequireEmail when authed user lacks email', () => {
    const user = makeUser({ email: '' });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/calendar']}>
        <Routes>
          <Route element={<EmailGate />}>
            <Route path="/calendar" element={<div>calendar</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: /add your email/i })).toBeInTheDocument();
    expect(screen.queryByText('calendar')).not.toBeInTheDocument();
  });

  it('logs out and lands on public calendar (not /login) when "not now" is clicked', async () => {
    const user = makeUser({ email: '' });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/members']}>
        <Routes>
          <Route element={<EmailGate />}>
            <Route path="/calendar" element={<div>calendar</div>} />
            <Route element={<RequireAuth />}>
              <Route path="/members" element={<div>members</div>} />
            </Route>
            <Route path="/login" element={<div>login</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /not now/i }));
    expect(useAuthStore.getState().status).toBe('unauthed');
    expect(useAuthStore.getState().user).toBeNull();
    expect(await screen.findByText('calendar')).toBeInTheDocument();
    expect(screen.queryByText('login')).not.toBeInTheDocument();
  });

  it('renders Outlet when authed user has email', () => {
    const user = makeUser({ email: 'foo@example.com' });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/calendar']}>
        <Routes>
          <Route element={<EmailGate />}>
            <Route path="/calendar" element={<div>calendar</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('calendar')).toBeInTheDocument();
  });

  it('renders Outlet for unauthed (null user)', () => {
    useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route element={<EmailGate />}>
            <Route path="/login" element={<div>login</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('login')).toBeInTheDocument();
  });

  it('renders Outlet when needs_onboarding (OnboardingGate handles routing)', () => {
    const user = makeUser({ email: '', needsOnboarding: true });
    useAuthStore.setState({ status: 'authed', user, accessToken: 'tok-abc' });

    render(
      <MemoryRouter initialEntries={['/onboarding']}>
        <Routes>
          <Route element={<EmailGate />}>
            <Route path="/onboarding" element={<div>onboarding</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('onboarding')).toBeInTheDocument();
  });
});
