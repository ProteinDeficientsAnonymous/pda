import { screen } from '@testing-library/react';
import type { ReactElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

import { setUnauthed } from '@/test/auth';
import { renderWithProviders } from '@/test/render';

import LoginScreen from './LoginScreen';

vi.mock('@/api/join', () => ({
  checkPhone: vi.fn(),
}));

vi.mock('@/api/client');

function renderWith(component: ReactElement) {
  return renderWithProviders(component, { route: '/login' });
}

beforeEach(() => {
  vi.clearAllMocks();
  setUnauthed();
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
