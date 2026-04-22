// Unit tests for the bottom nav. Covers all five destinations rendering,
// the add-event button navigating to /events/add, and the nav always
// mounting (no permission gate on the FAB).

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
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
  it('renders all five destinations: calendar, my events, add event, members, profile', () => {
    renderNav('/');

    expect(screen.getByRole('link', { name: /^calendar$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^my events$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^add event$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^members$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^profile$/i })).toBeInTheDocument();
  });

  it('my events link points at /events/mine', () => {
    renderNav('/');
    const link = screen.getByRole('link', { name: /^my events$/i });
    expect(link).toHaveAttribute('href', '/events/mine');
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
