import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import OnboardingScreen from './OnboardingScreen';
import { useAuthStore } from '@/auth/store';

vi.mock('@/auth/store', () => ({
  useAuthStore: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

vi.mock('@/screens/settings/AvatarUpload', () => ({
  AvatarUpload: () => <div data-testid="avatar-upload" />,
}));

describe('OnboardingScreen', () => {
  const completeOnboarding = vi.fn();
  const updateProfile = vi.fn();

  beforeEach(() => {
    completeOnboarding.mockReset();
    updateProfile.mockReset();
    updateProfile.mockResolvedValue(undefined);
    vi.mocked(useAuthStore).mockImplementation((selector) =>
      selector({ completeOnboarding, updateProfile, user: null } as never),
    );
  });

  it('shows email-required error when email is empty', async () => {
    render(
      <MemoryRouter>
        <OnboardingScreen />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/display name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'abcd1234ABCD!');
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(await screen.findByText(/email required/i)).toBeInTheDocument();
    expect(completeOnboarding).not.toHaveBeenCalled();
  });

  it('submits with required email', async () => {
    completeOnboarding.mockResolvedValue(undefined);
    render(
      <MemoryRouter>
        <OnboardingScreen />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/display name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/^email$/i), 'tester@example.com');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'abcd1234ABCD!');
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(completeOnboarding).toHaveBeenCalledWith({
      displayName: 'Tester',
      email: 'tester@example.com',
      newPassword: 'abcd1234ABCD!',
    });
  });

  it('advances to the profile step after successful account setup', async () => {
    completeOnboarding.mockResolvedValue(undefined);
    render(
      <MemoryRouter>
        <OnboardingScreen />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/display name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/^email$/i), 'tester@example.com');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'abcd1234ABCD!');
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(await screen.findByRole('button', { name: /^done$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /do this later/i })).toBeInTheDocument();
  });

  it('stays on the account step when account setup fails', async () => {
    completeOnboarding.mockRejectedValue(new Error('nope'));
    render(
      <MemoryRouter>
        <OnboardingScreen />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/display name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/^email$/i), 'tester@example.com');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'abcd1234ABCD!');
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(await screen.findByText(/couldn't finish onboarding/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^done$/i })).not.toBeInTheDocument();
  });
});
