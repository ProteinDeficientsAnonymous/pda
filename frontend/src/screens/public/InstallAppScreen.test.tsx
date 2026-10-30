import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import { useAuthStore } from '@/auth/store';
import { makeUser } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import InstallAppScreen from './InstallAppScreen';

const baseUser = makeUser({
  id: '1',
  phoneNumber: '+15551234567',
  email: 'test@example.com',
  weekStart: 'monday',
});

beforeEach(() => {
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
});

describe('InstallAppScreen', () => {
  it('renders page title and subtitle', () => {
    renderWithProviders(<InstallAppScreen />);
    expect(screen.getByRole('heading', { name: /install the app/i })).toBeInTheDocument();
    expect(
      screen.getByText(/add pda to your home screen for a native-app feel/i),
    ).toBeInTheDocument();
  });

  it('shows Android section', () => {
    renderWithProviders(<InstallAppScreen />);
    expect(screen.getByText(/^android$/i)).toBeInTheDocument();
  });

  it('shows iOS section', () => {
    renderWithProviders(<InstallAppScreen />);
    expect(screen.getByText(/iphone \/ ipad/i)).toBeInTheDocument();
  });

  it('shows step content for the initially-open platform', () => {
    renderWithProviders(<InstallAppScreen />);
    // jsdom's default UA doesn't match iOS or Android, so both cards open —
    // at minimum one of each platform's first-step labels should be visible.
    expect(screen.getByText(/open pda in safari/i)).toBeInTheDocument();
    expect(screen.getByText(/open pda in chrome/i)).toBeInTheDocument();
  });

  it('is accessible to unauthenticated user — renders without crash and key text visible', () => {
    useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
    renderWithProviders(<InstallAppScreen />);
    expect(screen.getByText(/add pda to your home screen/i)).toBeInTheDocument();
  });

  it('is accessible to authenticated user', () => {
    useAuthStore.setState({ status: 'authed', user: baseUser, accessToken: 'token' });
    renderWithProviders(<InstallAppScreen />);
    expect(screen.getByRole('heading', { name: /install the app/i })).toBeInTheDocument();
    expect(screen.getByText(/add pda to your home screen/i)).toBeInTheDocument();
  });
});
