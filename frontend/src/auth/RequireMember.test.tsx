import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';

import { makeUser } from '@/test/fixtures';

import { RequireMember } from './guards';
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
  afterEach(() => {
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
});
