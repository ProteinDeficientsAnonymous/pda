import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import ConsentScreen from './ConsentScreen';
import { useAuthStore } from '@/auth/store';

vi.mock('@/auth/store', () => ({
  useAuthStore: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

describe('ConsentScreen', () => {
  const acceptGuidelines = vi.fn();

  beforeEach(() => {
    acceptGuidelines.mockReset();
    vi.mocked(useAuthStore).mockImplementation((selector) =>
      selector({ acceptGuidelines } as never),
    );
  });

  it('disables continue until the checkbox is ticked', () => {
    render(
      <MemoryRouter>
        <ConsentScreen />
      </MemoryRouter>,
    );
    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled();
  });

  it('links to the public guidelines page', () => {
    render(
      <MemoryRouter>
        <ConsentScreen />
      </MemoryRouter>,
    );
    expect(screen.getByRole('link', { name: /community guidelines/i })).toHaveAttribute(
      'href',
      '/guidelines',
    );
  });

  it('accepts the guidelines once checked', async () => {
    acceptGuidelines.mockResolvedValue(undefined);
    render(
      <MemoryRouter>
        <ConsentScreen />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole('checkbox'));
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(acceptGuidelines).toHaveBeenCalledOnce();
  });

  it('shows a server error on failure', async () => {
    acceptGuidelines.mockRejectedValue(new Error('boom'));
    render(
      <MemoryRouter>
        <ConsentScreen />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole('checkbox'));
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
