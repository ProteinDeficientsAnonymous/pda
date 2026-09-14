import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as authApi from '@/api/auth';
import { useAuthStore } from '@/auth/store';
import { makeUser } from '@/test/fixtures';

import { VeganniversaryPrompt } from './VeganniversaryPrompt';

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  magicLogin: vi.fn(),
  restoreSession: vi.fn(),
  logout: vi.fn(),
  fetchMe: vi.fn(),
  completeOnboarding: vi.fn(),
  changePassword: vi.fn(),
  updateProfile: vi.fn().mockResolvedValue(undefined),
  uploadProfilePhoto: vi.fn(),
  deleteProfilePhoto: vi.fn(),
}));

const UNSEEN = makeUser({ hasSeenVeganniversary: false });

function renderPrompt(user = UNSEEN) {
  useAuthStore.setState({ status: 'authed', user, accessToken: 'tok' });
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <VeganniversaryPrompt />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
  vi.clearAllMocks();
  vi.mocked(authApi.updateProfile).mockResolvedValue({ ...UNSEEN, hasSeenVeganniversary: true });
});

describe('VeganniversaryPrompt', () => {
  it('opens when the user has not seen veganniversary yet', () => {
    renderPrompt();
    expect(screen.getByRole('dialog', { name: /veganniversary/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /edit veganniversary/i })).toBeInTheDocument();
    expect(
      screen.getByRole('switch', { name: /show veganniversary on my profile/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('switch', { name: /show my name in veganniversary shout out emails/i }),
    ).toBeInTheDocument();
  });

  it('does not open once the user has seen veganniversary', () => {
    renderPrompt(makeUser({ hasSeenVeganniversary: true }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('marks veganniversary as seen when done is clicked', async () => {
    const user = userEvent.setup();
    renderPrompt();
    await user.click(screen.getByRole('button', { name: /^done$/i }));
    await waitFor(() => {
      expect(authApi.updateProfile).toHaveBeenCalledWith({ hasSeenVeganniversary: true });
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('saves a filled veganniversary when done is clicked without save', async () => {
    const user = userEvent.setup();
    renderPrompt();
    await user.click(screen.getByRole('button', { name: /edit veganniversary/i }));
    await user.selectOptions(screen.getByLabelText(/^month$/i), 'june');
    await user.selectOptions(screen.getByLabelText(/^year$/i), '2020');
    await user.click(screen.getByRole('button', { name: /^done$/i }));
    await waitFor(() => {
      expect(authApi.updateProfile).toHaveBeenCalledWith({
        veganniversary: { month: 6, day: null, year: 2020 },
        hasSeenVeganniversary: true,
      });
    });
  });
});
