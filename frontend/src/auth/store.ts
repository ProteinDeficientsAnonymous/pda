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
import type { ConsentTypeValue } from '@/models/consent';
import type { User } from '@/models/user';

export type AuthStatus = 'idle' | 'loading' | 'authed' | 'unauthed';

interface AuthState {
  status: AuthStatus;
  user: User | null;
  accessToken: string | null;
  // True once the initial session-restore has resolved (to authed or
  // unauthed). Guards the app-level boot spinner so later 'loading' states
  // (login, magic-login) don't unmount the tree.
  booted: boolean;
  // Keeps OnboardingGate from bouncing /onboarding once account setup clears
  // needs_onboarding, so the optional profile step can render.
  profileStepActive: boolean;
  login: (phoneNumber: string, password: string) => Promise<void>;
  magicLogin: (token: string) => Promise<void>;
  restoreSession: () => Promise<void>;
  completeOnboarding: (payload: {
    newPassword: string;
    firstName?: string | undefined;
    lastName?: string | undefined;
    email?: string | undefined;
    pronouns?: string | undefined;
    consentTypes?: ConsentTypeValue[] | undefined;
  }) => Promise<void>;
  startProfileStep: () => void;
  finishProfileStep: () => void;
  acceptConsents: (consentTypes: ConsentTypeValue[]) => Promise<void>;
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
  booted: false,
  profileStepActive: false,

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
      set({ status: 'authed', user: result.user, accessToken: result.access, booted: true });
    } else {
      set({ status: 'unauthed', user: null, accessToken: null, booted: true });
    }
  },

  async completeOnboarding(payload) {
    const user = await authApi.completeOnboarding(payload);
    set({ user });
  },

  startProfileStep() {
    set({ profileStepActive: true });
  },

  finishProfileStep() {
    set({ profileStepActive: false });
  },

  async acceptConsents(consentTypes) {
    const user = await authApi.acceptConsents(consentTypes);
    set({ user });
  },

  async changePassword(current, next) {
    await authApi.changePassword(current, next);
  },

  async updateProfile(patch) {
    const user = await authApi.updateProfile(patch);
    set({ user });
    // The view-profile screen reads from its own ['member-profile', id] query,
    // which won't see store-only edits — invalidate so it refetches on next view.
    void queryClient.invalidateQueries({ queryKey: ['member-profile', user.id] });
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
    set({ status: 'unauthed', user: null, accessToken: null, profileStepActive: false });
  },

  forceLogout() {
    queryClient.clear();
    set({ status: 'unauthed', user: null, accessToken: null, profileStepActive: false });
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
