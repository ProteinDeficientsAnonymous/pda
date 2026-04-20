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
import { queryClient } from '@/api/queryClient';
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
  updateProfile: (patch: authApi.ProfileUpdate) => Promise<void>;
  uploadProfilePhoto: (file: File) => Promise<void>;
  deleteProfilePhoto: () => Promise<void>;
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
      queryClient.clear();
      set({ status: 'authed', user, accessToken: access });
    } catch (err) {
      set({ status: 'unauthed', user: null, accessToken: null });
      throw err;
    }
  },

  async magicLogin(token) {
    const prev = get();
    set({ status: 'loading' });
    try {
      const { access, user } = await authApi.magicLogin(token);
      queryClient.clear();
      set({ status: 'authed', user, accessToken: access });
    } catch (err) {
      // Preserve the existing session on failure. If the caller was already
      // signed in (e.g. they clicked someone else's magic link), forcibly
      // logging them out would compound the confusion. Only move to 'unauthed'
      // if there was no prior session.
      if (prev.status === 'authed' && prev.user) {
        set({ status: 'authed', user: prev.user, accessToken: prev.accessToken });
      } else {
        set({ status: 'unauthed', user: null, accessToken: null });
      }
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

  async updateProfile(patch) {
    const user = await authApi.updateProfile(patch);
    set({ user });
  },

  async uploadProfilePhoto(file) {
    const user = await authApi.uploadProfilePhoto(file);
    set({ user });
  },

  async deleteProfilePhoto() {
    const user = await authApi.deleteProfilePhoto();
    set({ user });
  },

  async refreshUser() {
    if (get().status !== 'authed') return;
    const user = await authApi.fetchMe();
    set({ user });
  },

  async logout() {
    await authApi.logout();
    queryClient.clear();
    set({ status: 'unauthed', user: null, accessToken: null });
  },

  forceLogout() {
    queryClient.clear();
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
