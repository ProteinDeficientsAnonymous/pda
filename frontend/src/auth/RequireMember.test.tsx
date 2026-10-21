import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { setStoredRsvpToken } from '@/api/rsvpTokenStorage';
import { makeUser } from '@/test/fixtures';

import { RequireAuth, RequireMember } from './guards';
import { useAuthStore } from './store';

function renderGuard() {
  return render(
    <MemoryRouter initialEntries={['/members']}>
      <Routes>
        <Route element={<RequireMember unlocks="see the member list" />}>
          <Route path="/members" element={<p>directory contents</p>} />
        </Route>
        <Route path="/login" element={<p>login screen</p>} />
        <Route path="/calendar" element={<p>calendar</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('RequireMember', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
    useAuthStore.setState({ status: 'idle', user: null, accessToken: null });
  });

  it('lets a full member through', () => {
    useAuthStore.setState({
      status: 'authed',
      user: makeUser({ isMember: true }),
      accessToken: 'tok',
    });
    renderGuard();
    expect(screen.getByText('directory contents')).toBeInTheDocument();
  });

  it('explains the gate to a tentatively-approved user instead of redirecting', () => {
    useAuthStore.setState({
      status: 'authed',
      user: makeUser({ isMember: false }),
      accessToken: 'tok',
    });
    renderGuard();

    expect(screen.queryByText('directory contents')).toBeNull();
    expect(screen.getByText(/you don.t have access to this page yet/i)).toBeInTheDocument();
    expect(
      screen.getByText(/come in person before we make you a full member/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/see the member list/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /see what.s coming up/i })).toBeInTheDocument();
  });

  it('sends an unauthed visitor to login with a redirect back', () => {
    renderGuard();
    expect(screen.getByText('login screen')).toBeInTheDocument();
  });

  it('shows the join notice to an unauthed public-rsvp visitor instead of redirecting', () => {
    setStoredRsvpToken('rsvp-tok');
    renderGuard();

    expect(screen.queryByText('login screen')).toBeNull();
    expect(screen.queryByText('directory contents')).toBeNull();
    expect(screen.getByText(/you can.t see this yet/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'request to join' })).toHaveAttribute('href', '/join');
    expect(screen.getByRole('link', { name: /already a member\? sign in/i })).toHaveAttribute(
      'href',
      '/login?redirect=%2Fmembers',
    );
  });
});

describe('RequireAuth join notice', () => {
  function renderAuth() {
    return render(
      <MemoryRouter initialEntries={['/profile']}>
        <Routes>
          <Route element={<RequireAuth />}>
            <Route path="/profile" element={<p>profile contents</p>} />
          </Route>
          <Route path="/login" element={<p>login screen</p>} />
        </Routes>
      </MemoryRouter>,
    );
  }

  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
    useAuthStore.setState({ status: 'idle', user: null, accessToken: null });
  });

  it('shows the join notice when unauthed with an rsvp token', () => {
    setStoredRsvpToken('rsvp-tok');
    renderAuth();
    expect(screen.getByText(/you can.t see this yet/i)).toBeInTheDocument();
    expect(screen.queryByText('login screen')).toBeNull();
  });

  it('still redirects to login with no rsvp token', () => {
    renderAuth();
    expect(screen.getByText('login screen')).toBeInTheDocument();
  });

  it('renders the outlet when authed even with an rsvp token', () => {
    setStoredRsvpToken('rsvp-tok');
    useAuthStore.setState({ status: 'authed', user: makeUser(), accessToken: 'tok' });
    renderAuth();
    expect(screen.getByText('profile contents')).toBeInTheDocument();
  });
});
