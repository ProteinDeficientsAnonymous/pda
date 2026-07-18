// Unit tests for the bottom nav. Covers the fixed destinations rendering,
// the auth-dependent my-rsvps tab, the add-event button navigating to
// /events/add, and the nav always mounting (no permission gate on the FAB).

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';

import { setStoredRsvpToken } from '@/api/rsvpTokenStorage';
import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';

import { BottomNav } from './BottomNav';

function LocationDisplay() {
  const loc = useLocation();
  return <span data-testid="pathname">{loc.pathname}</span>;
}

function renderNav(initialPath = '/') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route
          path="*"
          element={
            <>
              <BottomNav />
              <LocationDisplay />
            </>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('BottomNav', () => {
  afterEach(() => {
    useAuthStore.setState({ status: 'idle', user: null, accessToken: null });
  });

  it('renders calendar, add event, members, profile regardless of auth state', () => {
    renderNav('/');

    expect(screen.getByRole('link', { name: /^calendar$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^add event$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^members$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^profile$/i })).toBeInTheDocument();
  });

  it('authed users get a my rsvps link pointing at /events/mine', () => {
    useAuthStore.setState({
      status: 'authed',
      user: { profilePhotoUrl: '', photoUpdatedAt: null } as User,
      accessToken: 'token',
    });
    renderNav('/');

    const link = screen.getByRole('link', { name: /^my rsvps$/i });
    expect(link).toHaveAttribute('href', '/events/mine');
  });

  it('logged-out users with a stored rsvp token get a my rsvps link pointing at /my-rsvps', () => {
    setStoredRsvpToken('abc123');
    renderNav('/');

    const link = screen.getByRole('link', { name: /^my rsvps$/i });
    expect(link).toHaveAttribute('href', '/my-rsvps');
  });

  it('logged-out users with no stored rsvp token get no my rsvps tab', () => {
    renderNav('/');

    expect(screen.queryByRole('link', { name: /^my rsvps$/i })).not.toBeInTheDocument();
  });

  it('members link points at /members', () => {
    renderNav('/');
    const link = screen.getByRole('link', { name: /^members$/i });
    expect(link).toHaveAttribute('href', '/members');
  });

  it('add-event button navigates to /events/add', async () => {
    const user = userEvent.setup();
    renderNav('/');

    await user.click(screen.getByRole('button', { name: /^add event$/i }));

    expect(screen.getByTestId('pathname').textContent).toBe('/events/add');
  });

  it('renders regardless of route (no permission gate on the FAB)', () => {
    renderNav('/calendar');

    const nav = screen.getByRole('navigation', { name: /primary/i });
    expect(nav).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^add event$/i })).toBeInTheDocument();
  });
});
