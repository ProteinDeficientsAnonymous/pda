import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';
import InstallAppScreen from './InstallAppScreen';

const baseUser: User = {
  id: '1',
  phoneNumber: '+15551234567',
  displayName: 'Test User',
  email: 'test@example.com',
  bio: '',
  isSuperuser: false,
  isStaff: false,
  needsOnboarding: false,
  showPhone: false,
  showEmail: false,
  weekStart: 'monday',
  profilePhotoUrl: '',
  photoUpdatedAt: null,
  roles: [],
};

function renderWith(component: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{component}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
});

describe('InstallAppScreen', () => {
  it('renders page title', () => {
    renderWith(<InstallAppScreen />);
    expect(screen.getByRole('heading', { name: /install the app/i })).toBeInTheDocument();
  });

  it('shows Android section', () => {
    renderWith(<InstallAppScreen />);
    expect(screen.getByText(/android/i)).toBeInTheDocument();
  });

  it('shows iOS section', () => {
    renderWith(<InstallAppScreen />);
    expect(screen.getByText(/iphone \/ ipad/i)).toBeInTheDocument();
  });

  it('is accessible to unauthenticated user — renders without crash and key text visible', () => {
    useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
    renderWith(<InstallAppScreen />);
    expect(screen.getByText(/add pda to your home screen/i)).toBeInTheDocument();
  });

  it('is accessible to authenticated user', () => {
    useAuthStore.setState({ status: 'authed', user: baseUser, accessToken: 'token' });
    renderWith(<InstallAppScreen />);
    expect(screen.getByRole('heading', { name: /install the app/i })).toBeInTheDocument();
    expect(screen.getByText(/add pda to your home screen/i)).toBeInTheDocument();
  });
});
