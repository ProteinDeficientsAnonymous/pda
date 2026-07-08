import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type * as RouterDom from 'react-router-dom';
import ConsentScreen from './ConsentScreen';
import { useAuthStore } from '@/auth/store';

const navigate = vi.fn();
vi.mock('react-router-dom', async (importActual) => {
  const actual = await importActual<typeof RouterDom>();
  return { ...actual, useNavigate: () => navigate };
});

vi.mock('@/auth/store', () => ({
  useAuthStore: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

describe('ConsentScreen', () => {
  const acceptConsents = vi.fn();
  const logout = vi.fn();

  function mockStore({
    needsGuidelinesConsent = true,
    needsSmsConsent = false,
  }: { needsGuidelinesConsent?: boolean; needsSmsConsent?: boolean } = {}) {
    vi.mocked(useAuthStore).mockImplementation((selector) =>
      selector({
        acceptConsents,
        logout,
        user: { needsGuidelinesConsent, needsSmsConsent },
      } as never),
    );
  }

  beforeEach(() => {
    acceptConsents.mockReset();
    logout.mockReset();
    navigate.mockReset();
    mockStore();
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

  it('accepts the guidelines once checked and goes to calendar', async () => {
    acceptConsents.mockResolvedValue(undefined);
    render(
      <MemoryRouter>
        <ConsentScreen />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole('checkbox'));
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(acceptConsents).toHaveBeenCalledExactlyOnceWith(['guidelines']);
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/calendar', { replace: true }));
  });

  it('hides the sms checkbox when sms consent is not needed', () => {
    render(
      <MemoryRouter>
        <ConsentScreen />
      </MemoryRouter>,
    );
    expect(screen.queryByRole('link', { name: /sms policy/i })).not.toBeInTheDocument();
  });

  it('requires both checkboxes when sms consent is also needed', async () => {
    mockStore({ needsSmsConsent: true });
    render(
      <MemoryRouter>
        <ConsentScreen />
      </MemoryRouter>,
    );
    const continueBtn = screen.getByRole('button', { name: /continue/i });
    expect(continueBtn).toBeDisabled();
    await userEvent.click(screen.getByRole('checkbox', { name: /community guidelines/i }));
    expect(continueBtn).toBeDisabled();
    await userEvent.click(screen.getByRole('checkbox', { name: /sms policy/i }));
    expect(continueBtn).toBeEnabled();
  });

  it('submits all required consents when both are accepted', async () => {
    acceptConsents.mockResolvedValue(undefined);
    mockStore({ needsSmsConsent: true });
    render(
      <MemoryRouter>
        <ConsentScreen />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole('checkbox', { name: /community guidelines/i }));
    await userEvent.click(screen.getByRole('checkbox', { name: /sms policy/i }));
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(acceptConsents).toHaveBeenCalledExactlyOnceWith(['guidelines', 'sms']);
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/calendar', { replace: true }));
  });

  it('shows a server error on failure', async () => {
    acceptConsents.mockRejectedValue(new Error('boom'));
    render(
      <MemoryRouter>
        <ConsentScreen />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole('checkbox'));
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('logs out and returns to the landing page on "not now"', async () => {
    logout.mockResolvedValue(undefined);
    render(
      <MemoryRouter>
        <ConsentScreen />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole('button', { name: /not now/i }));
    expect(logout).toHaveBeenCalledOnce();
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/', { replace: true }));
    // "not now" is available without ticking the checkbox — it's a decline.
    expect(acceptConsents).not.toHaveBeenCalled();
  });

  it('allows "not now" even before the checkbox is ticked', () => {
    render(
      <MemoryRouter>
        <ConsentScreen />
      </MemoryRouter>,
    );
    expect(screen.getByRole('button', { name: /not now/i })).toBeEnabled();
  });
});
