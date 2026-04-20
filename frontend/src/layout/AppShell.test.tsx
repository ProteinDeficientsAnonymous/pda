import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from '@/auth/store';

// Stub modules that reach out to the network or browser APIs the AppShell
// pulls in transitively.
vi.mock('@/api/notifications', () => ({
  notificationKeys: { all: ['notifications'], list: [], unread: [] },
  useUnreadCount: vi.fn().mockReturnValue({ data: 0 }),
  useNotifications: vi.fn().mockReturnValue({ isPending: false, data: [] }),
  useMarkNotificationRead: vi.fn().mockReturnValue({ mutateAsync: vi.fn(), isPending: false }),
  useMarkAllNotificationsRead: vi.fn().mockReturnValue({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/hooks/useEventSource', () => ({
  useEventSource: vi.fn(),
}));

vi.mock('@/auth/useAuth', () => ({
  useHasAnyAdminPermission: vi.fn().mockReturnValue(false),
  useHasPermission: vi.fn().mockReturnValue(false),
}));

import { AppShell } from './AppShell';

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

// Helper that shows the current pathname so navigation tests can verify it.
function LocationDisplay() {
  const loc = useLocation();
  return <span data-testid="pathname">{loc.pathname}</span>;
}

function renderShell(initialPath = '/') {
  return render(
    <QueryClientProvider client={makeQc()}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<div>home</div>} />
            <Route path="/calendar" element={<div>calendar page</div>} />
            <Route path="/profile" element={<div>profile page</div>} />
            <Route path="/events/add" element={<div>add event page</div>} />
            <Route path="/login" element={<div>login page</div>} />
          </Route>
        </Routes>
        <LocationDisplay />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
  vi.clearAllMocks();
});

describe('AppShell + BottomNav', () => {
  it('renders expected nav destinations: calendar, add event, profile', () => {
    renderShell('/');

    // NavLinks use aria-label (screen-reader text) and the add button has aria-label too
    expect(screen.getByRole('link', { name: /^calendar$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^add event$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^profile$/i })).toBeInTheDocument();
  });

  it('tapping the calendar nav item navigates to /calendar', async () => {
    const user = userEvent.setup();
    renderShell('/');

    await user.click(screen.getByRole('link', { name: /^calendar$/i }));

    expect(screen.getByTestId('pathname').textContent).toBe('/calendar');
  });

  it('bottom nav is visible in the default jsdom viewport', () => {
    renderShell('/');

    const nav = screen.getByRole('navigation', { name: /primary/i });
    expect(nav).toBeInTheDocument();
  });
});
