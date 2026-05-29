import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import NewPasswordScreen from './NewPasswordScreen';
import { useAuthStore } from '@/auth/store';

vi.mock('@/auth/store', () => ({
  useAuthStore: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

const VALID = 'abcd1234ABCD!';

describe('NewPasswordScreen', () => {
  const completeOnboarding = vi.fn();

  beforeEach(() => {
    completeOnboarding.mockReset();
    vi.mocked(useAuthStore).mockImplementation((selector) =>
      selector({ completeOnboarding } as never),
    );
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

  it('submits the new password when confirmation matches', async () => {
    completeOnboarding.mockResolvedValue(undefined);
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
  });
});
