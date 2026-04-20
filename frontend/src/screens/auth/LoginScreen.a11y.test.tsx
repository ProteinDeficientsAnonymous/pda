import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';

vi.mock('@/api/join', () => ({
  checkPhone: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

import LoginScreen from './LoginScreen';
import { useAuthStore } from '@/auth/store';

function renderWith(component: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/login']}>{component}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
});

describe('LoginScreen accessibility', () => {
  it('has no axe violations on the phone step', async () => {
    const { container } = renderWith(<LoginScreen />);
    const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(results).toHaveNoViolations();
  }, 15000);

  it('continue action is discoverable by role', () => {
    renderWith(<LoginScreen />);
    expect(screen.getByRole('button', { name: /continue/i })).toBeInTheDocument();
  });

  it('phone step marks the identifier for password manager autofill', () => {
    renderWith(<LoginScreen />);
    const phoneInput = screen.getByRole('textbox', { name: /phone number/i });
    expect(phoneInput).toHaveAttribute('autocomplete', 'username');
    expect(phoneInput).toHaveAttribute('name', 'username');
  });
});
