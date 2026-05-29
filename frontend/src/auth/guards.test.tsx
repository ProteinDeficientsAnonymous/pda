import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { useAuthStore } from './store';
import { RequireAuth, RequirePermission, OnboardingGate, EmailGate } from './guards';
import { Permission } from '@/models/permissions';
import type { User } from '@/models/user';

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
    displayName: 'Alice',
    email: 'alice@example.com',
    bio: '',
    isSuperuser: false,
    isStaff: false,
    needsOnboarding: false,
    needsPasswordReset: false,
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

beforeEach(() => {
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
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
  it('redirects a first-time user (needsOnboarding=true, empty displayName) to /onboarding', () => {
    const user = makeUser({ needsOnboarding: true, displayName: '' });
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

  it('redirects a password-reset user (needsOnboarding=true, has displayName + email) to /new-password', () => {
    const user = makeUser({
      needsOnboarding: true,
      displayName: 'Alice',
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

  it('redirects a legacy user (needsOnboarding=true, has displayName but no email) to /onboarding', () => {
    // Pre-email-requirement users were approved with a displayName but never
    // supplied an email. On first login they must end up at /onboarding so
    // they can add one — /new-password has no email field and would loop.
    const user = makeUser({ needsOnboarding: true, displayName: 'Alice', email: '' });
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

  it('redirects a needsPasswordReset user (has displayName + email) to /new-password', () => {
    const user = makeUser({
      needsOnboarding: false,
      needsPasswordReset: true,
      displayName: 'Bob',
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
      displayName: 'Bob',
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

    expect(screen.getByText(/add your email/i)).toBeInTheDocument();
    expect(screen.queryByText('calendar')).not.toBeInTheDocument();
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
