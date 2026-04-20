import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';

const submitFeedbackMock = vi.fn();
const useSubmitFeedbackMock =
  vi.fn<() => { mutateAsync: typeof submitFeedbackMock; isPending: boolean }>();

vi.mock('@/api/feedback', () => ({
  useSubmitFeedback: () => useSubmitFeedbackMock(),
}));

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { FeedbackButton } from './FeedbackButton';

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 'user-1',
    phoneNumber: '+12125551234',
    displayName: 'alice',
    email: 'alice@example.com',
    bio: '',
    isSuperuser: false,
    isStaff: false,
    needsOnboarding: false,
    showPhone: false,
    showEmail: false,
    weekStart: 'sunday',
    profilePhotoUrl: '',
    photoUpdatedAt: null,
    roles: [],
    ...overrides,
  };
}

function renderButton() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/calendar']}>
        <FeedbackButton />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ status: 'authed', user: makeUser(), accessToken: 'tok' });
  submitFeedbackMock.mockResolvedValue({ html_url: 'https://example.com/1' });
  useSubmitFeedbackMock.mockReturnValue({
    mutateAsync: submitFeedbackMock,
    isPending: false,
  });
});

describe('FeedbackButton accessibility', () => {
  it('has no axe violations for the closed floating button', async () => {
    const { container } = renderButton();
    const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(results).toHaveNoViolations();
  }, 15000);

  it('has no axe violations when the feedback form is open', async () => {
    const user = userEvent.setup();
    const { container } = renderButton();

    await user.click(screen.getByRole('button', { name: /send feedback/i }));
    expect(screen.getByRole('dialog', { name: /send feedback/i })).toBeInTheDocument();

    const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(results).toHaveNoViolations();
  }, 15000);

  it('floating trigger is discoverable by role with an accessible label', () => {
    renderButton();
    expect(screen.getByRole('button', { name: /send feedback/i })).toBeInTheDocument();
  });

  it('open form exposes labeled title, description, and submit controls by role', async () => {
    const user = userEvent.setup();
    renderButton();

    await user.click(screen.getByRole('button', { name: /send feedback/i }));

    expect(screen.getByRole('dialog', { name: /send feedback/i })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /^title$/i })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /^description$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^submit$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });
});
