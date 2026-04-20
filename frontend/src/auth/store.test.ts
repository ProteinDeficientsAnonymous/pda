import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from './store';
import type { User } from '@/models/user';

// Mock the api/auth module so no real HTTP calls are made.
vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  magicLogin: vi.fn(),
  restoreSession: vi.fn(),
  logout: vi.fn(),
  fetchMe: vi.fn(),
  completeOnboarding: vi.fn(),
  changePassword: vi.fn(),
  updateProfile: vi.fn(),
  uploadProfilePhoto: vi.fn(),
  deleteProfilePhoto: vi.fn(),
}));

// Also mock the client so setAuthBridge (called at store module load) doesn't
// set up real axios interceptors in the test environment.
vi.mock('@/api/client', () => ({
  setAuthBridge: vi.fn(),
  authClient: { post: vi.fn(), get: vi.fn() },
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import * as authApi from '@/api/auth';

const mockUser: User = {
  id: 'user-1',
  phoneNumber: '+12125551234',
  displayName: 'Alice',
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
};

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ status: 'idle', user: null, accessToken: null });
});

describe('useAuthStore', () => {
  describe('restoreSession', () => {
    it('sets status to unauthed and clears user when there is no existing session', async () => {
      vi.mocked(authApi.restoreSession).mockResolvedValueOnce(null);

      await useAuthStore.getState().restoreSession();

      const { status, user, accessToken } = useAuthStore.getState();
      expect(status).toBe('unauthed');
      expect(user).toBeNull();
      expect(accessToken).toBeNull();
    });
  });

  describe('login', () => {
    it('sets status to authed and populates user on success', async () => {
      vi.mocked(authApi.login).mockResolvedValueOnce({ access: 'tok-abc', user: mockUser });

      await useAuthStore.getState().login('+12125551234', 'password123');

      const { status, user } = useAuthStore.getState();
      expect(status).toBe('authed');
      expect(user).toEqual(mockUser);
    });

    it('stores the access token in state on successful login', async () => {
      vi.mocked(authApi.login).mockResolvedValueOnce({ access: 'tok-abc', user: mockUser });

      await useAuthStore.getState().login('+12125551234', 'password123');

      expect(useAuthStore.getState().accessToken).toBe('tok-abc');
    });

    it('sets status to unauthed and re-throws on a 401 response', async () => {
      const err = Object.assign(new Error('401'), {
        isAxiosError: true,
        response: { status: 401 },
      });
      vi.mocked(authApi.login).mockRejectedValueOnce(err);

      await expect(
        useAuthStore.getState().login('+12125551234', 'wrongpassword'),
      ).rejects.toThrow('401');

      const { status, user, accessToken } = useAuthStore.getState();
      expect(status).toBe('unauthed');
      expect(user).toBeNull();
      expect(accessToken).toBeNull();
    });

    it('sets status to unauthed and re-throws on a network error', async () => {
      const err = Object.assign(new Error('Network Error'), { isAxiosError: true });
      vi.mocked(authApi.login).mockRejectedValueOnce(err);

      await expect(
        useAuthStore.getState().login('+12125551234', 'password123'),
      ).rejects.toThrow('Network Error');

      expect(useAuthStore.getState().status).toBe('unauthed');
    });

    it('sets status to unauthed and re-throws on a 500 response', async () => {
      const err = Object.assign(new Error('500'), {
        isAxiosError: true,
        response: { status: 500 },
      });
      vi.mocked(authApi.login).mockRejectedValueOnce(err);

      await expect(
        useAuthStore.getState().login('+12125551234', 'password123'),
      ).rejects.toThrow('500');

      expect(useAuthStore.getState().status).toBe('unauthed');
    });
  });

  describe('magicLogin', () => {
    it('preserves the existing session when magic login fails', async () => {
      useAuthStore.setState({ status: 'authed', user: mockUser, accessToken: 'tok-abc' });
      const err = Object.assign(new Error('403'), {
        isAxiosError: true,
        response: { status: 403 },
      });
      vi.mocked(authApi.magicLogin).mockRejectedValueOnce(err);

      await expect(useAuthStore.getState().magicLogin('some-token')).rejects.toThrow('403');

      const { status, user, accessToken } = useAuthStore.getState();
      expect(status).toBe('authed');
      expect(user).toEqual(mockUser);
      expect(accessToken).toBe('tok-abc');
    });

    it('moves to unauthed when magic login fails and no prior session existed', async () => {
      const err = Object.assign(new Error('400'), {
        isAxiosError: true,
        response: { status: 400 },
      });
      vi.mocked(authApi.magicLogin).mockRejectedValueOnce(err);

      await expect(useAuthStore.getState().magicLogin('some-token')).rejects.toThrow('400');

      expect(useAuthStore.getState().status).toBe('unauthed');
    });
  });

  describe('logout', () => {
    it('sets status to unauthed and clears user and accessToken', async () => {
      // Start in an authed state.
      useAuthStore.setState({ status: 'authed', user: mockUser, accessToken: 'tok-abc' });
      vi.mocked(authApi.logout).mockResolvedValueOnce(undefined);

      await useAuthStore.getState().logout();

      const { status, user, accessToken } = useAuthStore.getState();
      expect(status).toBe('unauthed');
      expect(user).toBeNull();
      expect(accessToken).toBeNull();
    });
  });

  describe('forceLogout', () => {
    it('synchronously sets status to unauthed and clears user and accessToken', () => {
      useAuthStore.setState({ status: 'authed', user: mockUser, accessToken: 'tok-abc' });

      useAuthStore.getState().forceLogout();

      const { status, user, accessToken } = useAuthStore.getState();
      expect(status).toBe('unauthed');
      expect(user).toBeNull();
      expect(accessToken).toBeNull();
    });
  });
});
