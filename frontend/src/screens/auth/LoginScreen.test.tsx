import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/join', () => ({
  checkPhone: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

import { useAuthStore } from '@/auth/store';

import LoginScreen from './LoginScreen';

function renderAt(entry: { pathname: string; state?: unknown }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[entry]}>
        <LoginScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
});

describe('LoginScreen phone prefill', () => {
  it('starts on the password step when a valid phone arrives in router state', () => {
    renderAt({ pathname: '/login', state: { phone: '+14155550123' } });

    expect(screen.getByLabelText('password')).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: /phone number/i })).not.toBeInTheDocument();
  });

  it('starts on the phone step with no state', () => {
    renderAt({ pathname: '/login' });

    expect(screen.getByRole('textbox', { name: /phone number/i })).toBeInTheDocument();
    expect(screen.queryByLabelText('password')).not.toBeInTheDocument();
  });

  it('ignores an invalid phone in state and stays on the phone step', () => {
    renderAt({ pathname: '/login', state: { phone: 'not-a-phone' } });

    expect(screen.getByRole('textbox', { name: /phone number/i })).toBeInTheDocument();
    expect(screen.queryByLabelText('password')).not.toBeInTheDocument();
  });
});
