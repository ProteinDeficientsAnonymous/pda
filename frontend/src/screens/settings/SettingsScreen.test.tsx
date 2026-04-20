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

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from '@/auth/store';
import { useAccessibilityStore } from '@/accessibility/store';
import type { User } from '@/models/user';

// Stub heavy sub-components that have their own API/DOM dependencies
vi.mock('./AvatarUpload', () => ({
  AvatarUpload: () => <div data-testid="avatar-upload" />,
}));

vi.mock('./ChangePasswordDialog', () => ({
  ChangePasswordDialog: () => null,
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

import SettingsScreen from './SettingsScreen';

const TEST_USER: User = {
  id: 'u1',
  phoneNumber: '+12125550001',
  displayName: 'Test User',
  email: 'test@example.com',
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
});
