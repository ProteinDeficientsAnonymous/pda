// Zustand auth store.
//
// State machine:
//   idle      — before session restore has run (app boot)
//   loading   — a login/restore is in flight
//   authed    — user + accessToken present; API calls authorized
//   unauthed  — no session; login required
//
// The access token lives in memory only. The refresh token is an httpOnly cookie
// managed by the server — we never touch it from JS. On reload, `restoreSession`
// calls /api/auth/refresh/ (cookie is sent automatically) and rehydrates.

import { create } from 'zustand';
import * as authApi from '@/api/auth';
import { setAuthBridge } from '@/api/client';
import type { User } from '@/models/user';

export type AuthStatus = 'idle' | 'loading' | 'authed' | 'unauthed';

interface AuthState {
  status: AuthStatus;
  user: User | null;
  accessToken: string | null;
  login: (phoneNumber: string, password: string) => Promise<void>;
  magicLogin: (token: string) => Promise<void>;
  restoreSession: () => Promise<void>;
  completeOnboarding: (payload: {
    newPassword: string;
    displayName?: string | undefined;
    email?: string | undefined;
  }) => Promise<void>;
  changePassword: (current: string, next: string) => Promise<void>;
  refreshUser: () => Promise<void>;
  logout: () => Promise<void>;
  // Invoked by axios when a refresh fails — synchronous, no await.
  forceLogout: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  status: 'idle',
  user: null,
  accessToken: null,

  async login(phoneNumber, password) {
    set({ status: 'loading' });
    try {
      const { access, user } = await authApi.login(phoneNumber, password);
      set({ status: 'authed', user, accessToken: access });
    } catch (err) {
      set({ status: 'unauthed', user: null, accessToken: null });
      throw err;
    }
  },

  async magicLogin(token) {
    set({ status: 'loading' });
    try {
      const { access, user } = await authApi.magicLogin(token);
      set({ status: 'authed', user, accessToken: access });
    } catch (err) {
      set({ status: 'unauthed', user: null, accessToken: null });
      throw err;
    }
  },

  async restoreSession() {
    set({ status: 'loading' });
    const result = await authApi.restoreSession();
    if (result) {
      set({ status: 'authed', user: result.user, accessToken: result.access });
    } else {
      set({ status: 'unauthed', user: null, accessToken: null });
    }
  },

  async completeOnboarding(payload) {
    const user = await authApi.completeOnboarding(payload);
    set({ user });
  },

  async changePassword(current, next) {
    await authApi.changePassword(current, next);
  },

  async refreshUser() {
    if (get().status !== 'authed') return;
    const user = await authApi.fetchMe();
    set({ user });
  },

  async logout() {
    await authApi.logout();
    set({ status: 'unauthed', user: null, accessToken: null });
  },

  forceLogout() {
    set({ status: 'unauthed', user: null, accessToken: null });
  },
}));

// Wire axios → store. Called once at module load; client.ts uses the bridge
// instead of importing the store directly to break the cycle.
setAuthBridge({
  getAccessToken: () => useAuthStore.getState().accessToken,
  setAccessToken: (token) => {
    useAuthStore.setState({ accessToken: token });
  },
  onSessionExpired: () => {
    useAuthStore.getState().forceLogout();
  },
});
