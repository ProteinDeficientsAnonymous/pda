import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';
import { makeUser as makeSharedUser } from '@/test/fixtures';

import OnboardingScreen from './OnboardingScreen';

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

function makeUser(overrides: Partial<User> = {}): User {
  return makeSharedUser({
    id: 'u1',
    firstName: '',
    lastName: '',
    fullName: '',
    needsOnboarding: true,
    ...overrides,
  });
}

describe('OnboardingScreen', () => {
  const completeOnboarding = vi.fn();
  const updateProfile = vi.fn();
  const finishProfileStep = vi.fn();

  function setupMock(user: User, profileStepActive = false) {
    const storeState = {
      completeOnboarding,
      updateProfile,
      finishProfileStep,
      user,
      profileStepActive,
    };
    // Cast via `as never` so partial state satisfies the full AuthState type.
    vi.mocked(useAuthStore).mockImplementation(
      Object.assign((selector: (s: typeof storeState) => unknown) => selector(storeState), {
        getState: () => ({ user }),
      }) as never,
    );
  }

  beforeEach(() => {
    completeOnboarding.mockReset();
    updateProfile.mockReset();
    finishProfileStep.mockReset();
    updateProfile.mockResolvedValue(undefined);
    setupMock(makeUser());
  });

  it('shows email-required error when email is empty', async () => {
    setupMock(makeUser({ needsGuidelinesConsent: false, needsSmsConsent: false }));
    render(
      <MemoryRouter>
        <OnboardingScreen />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/first name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'abcd1234ABCD!');
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(await screen.findByText(/email required/i)).toBeInTheDocument();
    expect(completeOnboarding).not.toHaveBeenCalled();
  });

  it('submits with required email (no consent checkboxes for already-consented user)', async () => {
    completeOnboarding.mockResolvedValue(undefined);
    setupMock(makeUser({ needsGuidelinesConsent: false, needsSmsConsent: false }));
    render(
      <MemoryRouter>
        <OnboardingScreen />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/first name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/last name/i), 'McTest');
    await userEvent.type(screen.getByLabelText(/^email$/i), 'tester@example.com');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'abcd1234ABCD!');
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(completeOnboarding).toHaveBeenCalledWith({
      firstName: 'Tester',
      lastName: 'McTest',
      email: 'tester@example.com',
      newPassword: 'abcd1234ABCD!',
      consentTypes: [],
      startProfileStep: true,
    });
  });

  it('passes an entered pronoun through to completeOnboarding', async () => {
    completeOnboarding.mockResolvedValue(undefined);
    setupMock(makeUser({ needsGuidelinesConsent: false, needsSmsConsent: false }));
    render(
      <MemoryRouter>
        <OnboardingScreen />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/first name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/^email$/i), 'tester@example.com');
    await userEvent.type(screen.getByLabelText(/pronouns/i), 'they/them');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'abcd1234ABCD!');
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(completeOnboarding).toHaveBeenCalledWith({
      firstName: 'Tester',
      lastName: '',
      email: 'tester@example.com',
      pronouns: 'they/them',
      newPassword: 'abcd1234ABCD!',
      consentTypes: [],
      startProfileStep: true,
    });
  });

  it('does not render consent checkboxes when user already consented to both', () => {
    setupMock(makeUser({ needsGuidelinesConsent: false, needsSmsConsent: false }));
    render(
      <MemoryRouter>
        <OnboardingScreen />
      </MemoryRouter>,
    );
    expect(screen.queryByLabelText(/community guidelines/i)).toBeNull();
    expect(screen.queryByLabelText(/sms policy/i)).toBeNull();
  });

  it('renders both checkboxes and blocks submit until both are checked', async () => {
    completeOnboarding.mockResolvedValue(undefined);
    setupMock(makeUser({ needsGuidelinesConsent: true, needsSmsConsent: true }));
    render(
      <MemoryRouter>
        <OnboardingScreen />
      </MemoryRouter>,
    );

    // Both checkboxes must be present
    const [guidelinesBox, smsBox] = screen.getAllByRole('checkbox') as [HTMLElement, HTMLElement];

    // Fill in the text fields
    await userEvent.type(screen.getByLabelText(/first name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/^email$/i), 'tester@example.com');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'abcd1234ABCD!');

    // Button should be disabled while neither box is checked
    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled();

    // Check first box — still blocked
    await userEvent.click(guidelinesBox);
    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled();

    // Check second box — now unblocked
    await userEvent.click(smsBox);
    expect(screen.getByRole('button', { name: /continue/i })).not.toBeDisabled();

    // Submit and verify both consent types passed through
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(completeOnboarding).toHaveBeenCalledWith({
      firstName: 'Tester',
      lastName: '',
      email: 'tester@example.com',
      newPassword: 'abcd1234ABCD!',
      consentTypes: ['guidelines', 'sms'],
      startProfileStep: true,
    });
  });

  it('requests the profile step in the same completeOnboarding call', async () => {
    completeOnboarding.mockResolvedValue(undefined);
    render(
      <MemoryRouter>
        <OnboardingScreen />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/first name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/^email$/i), 'tester@example.com');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'abcd1234ABCD!');
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(completeOnboarding).toHaveBeenCalledTimes(1);
    expect(completeOnboarding).toHaveBeenCalledWith(
      expect.objectContaining({ startProfileStep: true }),
    );
    expect(screen.queryByText(/couldn't finish onboarding/i)).not.toBeInTheDocument();
  });

  it('renders the profile step when profileStepActive is set', () => {
    setupMock(makeUser({ needsOnboarding: false }), true);
    render(
      <MemoryRouter>
        <OnboardingScreen />
      </MemoryRouter>,
    );
    expect(screen.getByRole('button', { name: /^done$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /do this later/i })).toBeInTheDocument();
  });

  it('stays on the account step when account setup fails', async () => {
    completeOnboarding.mockRejectedValue(new Error('nope'));
    render(
      <MemoryRouter>
        <OnboardingScreen />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/first name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/^email$/i), 'tester@example.com');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'abcd1234ABCD!');
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(await screen.findByText(/couldn't finish onboarding/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^done$/i })).not.toBeInTheDocument();
  });
});
