import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';
import { makeUser } from '@/test/fixtures';

import NewPasswordScreen from './NewPasswordScreen';

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

const VALID = 'abcd1234ABCD!';

describe('NewPasswordScreen', () => {
  const completeOnboarding = vi.fn();
  const startProfileStep = vi.fn();
  const finishProfileStep = vi.fn();

  function setupMock(user: User, profileStepActive = false) {
    const storeState = {
      completeOnboarding,
      startProfileStep,
      finishProfileStep,
      user,
      profileStepActive,
    };
    vi.mocked(useAuthStore).mockImplementation(
      Object.assign((selector: (s: typeof storeState) => unknown) => selector(storeState), {
        getState: () => ({ user }),
      }) as never,
    );
  }

  beforeEach(() => {
    completeOnboarding.mockReset();
    startProfileStep.mockReset();
    finishProfileStep.mockReset();
    setupMock(makeUser({ needsOnboarding: false, needsPasswordReset: true }));
  });

  it('blocks submit when confirmation does not match', async () => {
    render(
      <MemoryRouter>
        <NewPasswordScreen />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/^new password$/i), VALID);
    await userEvent.type(screen.getByLabelText(/confirm new password/i), `${VALID}x`);
    await userEvent.click(screen.getByRole('button', { name: /save password/i }));

    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
    expect(completeOnboarding).not.toHaveBeenCalled();
  });

  it('submits the new password when confirmation matches, and does not enter the profile step on a real password reset', async () => {
    completeOnboarding.mockResolvedValue(undefined);
    setupMock(makeUser({ needsOnboarding: false, needsPasswordReset: true }));
    render(
      <MemoryRouter>
        <NewPasswordScreen />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/^new password$/i), VALID);
    await userEvent.type(screen.getByLabelText(/confirm new password/i), VALID);
    await userEvent.click(screen.getByRole('button', { name: /save password/i }));

    await vi.waitFor(() => {
      expect(completeOnboarding).toHaveBeenCalledWith({ newPassword: VALID });
    });
    // a self-service password reset is an already-onboarded member — no profile step
    expect(startProfileStep).not.toHaveBeenCalled();
  });

  it('enters the profile step after a first-time join-request user sets their password', async () => {
    completeOnboarding.mockResolvedValue(undefined);
    setupMock(makeUser({ needsOnboarding: true, needsPasswordReset: false }));
    render(
      <MemoryRouter>
        <NewPasswordScreen />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/^new password$/i), VALID);
    await userEvent.type(screen.getByLabelText(/confirm new password/i), VALID);
    await userEvent.click(screen.getByRole('button', { name: /save password/i }));

    await vi.waitFor(() => {
      expect(completeOnboarding).toHaveBeenCalledWith({ newPassword: VALID });
    });
    expect(startProfileStep).toHaveBeenCalledTimes(1);
  });

  it('renders the profile step when profileStepActive is set', () => {
    setupMock(makeUser({ needsOnboarding: true }), true);
    render(
      <MemoryRouter>
        <NewPasswordScreen />
      </MemoryRouter>,
    );
    expect(screen.getByRole('button', { name: /^done$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /do this later/i })).toBeInTheDocument();
  });
});
