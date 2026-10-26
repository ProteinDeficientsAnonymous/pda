import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type * as RouterDom from 'react-router-dom';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { updateProfile } from '@/api/auth';
import { useAuthStore } from '@/auth/store';

import ConsentScreen from './ConsentScreen';

const navigate = vi.fn();
vi.mock('react-router-dom', async (importActual) => {
  const actual = await importActual<typeof RouterDom>();
  return { ...actual, useNavigate: () => navigate };
});

vi.mock('@/auth/store', () => ({
  useAuthStore: vi.fn(),
}));

vi.mock('@/api/auth', async (importActual) => ({
  ...(await importActual<object>()),
  updateProfile: vi.fn(),
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
    needsContactPrivacyConsent = false,
  }: {
    needsGuidelinesConsent?: boolean;
    needsSmsConsent?: boolean;
    needsContactPrivacyConsent?: boolean;
  } = {}) {
    vi.mocked(useAuthStore).mockImplementation((selector) =>
      selector({
        acceptConsents,
        logout,
        user: { needsGuidelinesConsent, needsSmsConsent, needsContactPrivacyConsent },
      } as never),
    );
  }

  beforeEach(() => {
    acceptConsents.mockReset();
    logout.mockReset();
    vi.mocked(updateProfile).mockReset();
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

  it('saves privacy toggles before recording consent on the privacy-only check', async () => {
    vi.mocked(updateProfile).mockResolvedValue(undefined as never);
    acceptConsents.mockResolvedValue(undefined);
    mockStore({ needsGuidelinesConsent: false, needsContactPrivacyConsent: true });
    render(
      <MemoryRouter>
        <ConsentScreen />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(updateProfile).toHaveBeenCalledExactlyOnceWith({ showPhone: true, showEmail: true });
    expect(acceptConsents).toHaveBeenCalledExactlyOnceWith(['contact_privacy']);
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/calendar', { replace: true }));
  });

  it.each([
    ['guidelines', { needsGuidelinesConsent: true }],
    ['privacy', { needsGuidelinesConsent: false, needsContactPrivacyConsent: true }],
  ])('warns that "not now" logs out on the %s check', (_, flags) => {
    mockStore(flags);
    render(
      <MemoryRouter>
        <ConsentScreen />
      </MemoryRouter>,
    );
    expect(screen.getByText(/"not now" logs you out/i)).toBeInTheDocument();
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
