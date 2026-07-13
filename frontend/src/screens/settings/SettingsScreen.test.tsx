// localStorage must be available before Zustand `persist` loads.
// vi.hoisted runs at the top of the module, before any imports are evaluated.
const storageMock = vi.hoisted(() => {
  let store: Record<string, string> = {};
  const mock = {
    getItem: (key: string): string | null => store[key] ?? null,
    setItem: (key: string, value: string): void => {
      store[key] = value;
    },
    removeItem: (key: string): void => {
      delete store[key];
    },
    clear: (): void => {
      store = {};
    },
    get length(): number {
      return Object.keys(store).length;
    },
    key: (index: number): string | null => Object.keys(store)[index] ?? null,
  };
  Object.defineProperty(window, 'localStorage', { value: mock, writable: true });
  return mock;
});

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAccessibilityStore } from '@/accessibility/store';
import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';

// Stub heavy sub-components that have their own API/DOM dependencies
vi.mock('./AvatarUpload', () => ({
  AvatarUpload: () => <div data-testid="avatar-upload" />,
}));

vi.mock('./ChangePasswordDialog', () => ({
  ChangePasswordDialog: () => null,
}));

// CalendarFeedSubscription fires a real apiClient request (useCalendarToken).
// Without a server the axios interceptor treats the 401 as session-expired and
// force-logs-out the store mid-test — nulling `user`, so SettingsScreen renders
// null and the DOM empties. Stub it like the other API-backed sub-components.
vi.mock('./CalendarFeedSubscription', () => ({
  CalendarFeedSubscription: () => null,
}));

// updateProfile is called as a mutation on the store — stub it so tests don't
// hit the real API
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

import * as authApi from '@/api/auth';

import SettingsScreen from './SettingsScreen';

const TEST_USER: User = {
  id: 'u1',
  phoneNumber: '+12125550001',
  firstName: 'Test',
  lastName: 'User',
  fullName: 'Test User',
  nickname: '',
  email: 'test@example.com',
  bio: '',
  pronouns: '',
  isSuperuser: false,
  isStaff: false,
  needsOnboarding: false,
  needsPasswordReset: false,
  needsGuidelinesConsent: false,
  needsSmsConsent: false,
  showPhone: false,
  showEmail: false,
  hideLastName: false,
  weekStart: 'sunday',
  calendarFeedScope: 'all',
  profilePhotoUrl: '',
  photoUpdatedAt: null,
  roles: [],
};

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderSettings() {
  return render(
    <QueryClientProvider client={makeQc()}>
      <MemoryRouter>
        <SettingsScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  storageMock.clear();
  useAuthStore.setState({ status: 'authed', user: TEST_USER, accessToken: 'tok' });
  useAccessibilityStore.setState({ themeMode: 'system', dyslexiaFont: false, textScale: 1.0 });
  vi.clearAllMocks();
  // The store's updateProfile reads .id off the resolved user; resolve a real one
  // so toggles that call it directly don't hit an undefined-deref.
  vi.mocked(authApi.updateProfile).mockResolvedValue(TEST_USER);
});

describe('SettingsScreen', () => {
  it("renders theme mode options with 'system' selected by default", () => {
    renderSettings();

    const radioGroup = screen.getByRole('radiogroup', { name: /^theme$/i });
    expect(radioGroup).toBeInTheDocument();

    const systemRadio = screen.getByRole('radio', { name: /^system$/i });
    expect(systemRadio).toBeChecked();

    expect(screen.getByRole('radio', { name: /^light$/i })).not.toBeChecked();
    expect(screen.getByRole('radio', { name: /^dark$/i })).not.toBeChecked();
  });

  it("selecting 'dark' updates accessibility store themeMode to 'dark'", async () => {
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByRole('radio', { name: /^dark$/i }));

    await waitFor(() => {
      expect(useAccessibilityStore.getState().themeMode).toBe('dark');
    });
  });

  it('toggling "hide my last name" calls updateProfile with hideLastName true', async () => {
    const user = userEvent.setup();
    renderSettings();

    await user.click(
      screen.getByRole('checkbox', { name: /hide my last name from other members/i }),
    );

    await waitFor(() => {
      expect(authApi.updateProfile).toHaveBeenCalledWith({ hideLastName: true });
    });
  });

  it('saves an edited pronouns value via updateProfile', async () => {
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByRole('button', { name: /edit pronouns/i }));
    const field = screen.getByLabelText(/^pronouns$/i);
    await user.type(field, 'they/them');
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    await waitFor(() => {
      expect(authApi.updateProfile).toHaveBeenCalledWith({ pronouns: 'they/them' });
    });
  });

  it('saves an edited nickname value via updateProfile', async () => {
    const authApi = await import('@/api/auth');
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByRole('button', { name: /edit nickname/i }));
    const field = screen.getByLabelText(/^nickname$/i);
    await user.type(field, 'Birdie');
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    await waitFor(() => {
      expect(authApi.updateProfile).toHaveBeenCalledWith({ nickname: 'Birdie' });
    });
  });

  it('saves an edited first name via updateProfile', async () => {
    const authApi = await import('@/api/auth');
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByRole('button', { name: /edit first name/i }));
    const field = screen.getByLabelText(/^first name$/i);
    await user.clear(field);
    await user.type(field, 'Newname');
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    await waitFor(() => {
      expect(authApi.updateProfile).toHaveBeenCalledWith({ firstName: 'Newname' });
    });
  });

  it('saves an edited last name via updateProfile', async () => {
    const authApi = await import('@/api/auth');
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByRole('button', { name: /edit last name/i }));
    const field = screen.getByLabelText(/^last name$/i);
    await user.clear(field);
    await user.type(field, 'Newlast');
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    await waitFor(() => {
      expect(authApi.updateProfile).toHaveBeenCalledWith({ lastName: 'Newlast' });
    });
  });

  it('surfaces the error when saving an email that is already in use', async () => {
    vi.mocked(authApi.updateProfile).mockRejectedValueOnce({
      isAxiosError: true,
      response: {
        status: 409,
        data: { detail: [{ code: 'email.already_exists', field: 'email' }] },
      },
    });
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByRole('button', { name: /edit email/i }));
    const field = screen.getByLabelText(/^email$/i);
    await user.clear(field);
    await user.type(field, 'taken@example.com');
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    expect(await screen.findByText(/already on another account/i)).toBeInTheDocument();
    // Field stays in edit mode so the user can correct it.
    expect(screen.getByRole('button', { name: /^save$/i })).toBeInTheDocument();
  });
});
