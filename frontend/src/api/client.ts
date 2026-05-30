// axios client with a Completer-style refresh lock.
//
// Two instances:
//   - `authClient`  — no interceptors. Used for /login/, /magic-login/, /refresh/,
//                     /logout/. Avoids the interceptor calling itself on 401.
//   - `apiClient`   — attaches `Authorization: Bearer <access>` from the auth store,
//                     and on a 401 refreshes via a single shared in-flight promise
//                     (the Dio `_refreshLock` Completer port).
//
// Both instances send cookies (`withCredentials`) so the httpOnly refresh cookie
// reaches the server on cross-origin dev (React :3000 → Django :8000).

import axios, {
  isAxiosError,
  type AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios';
import { API_BASE_URL } from '@/config/env';

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

// Lifted out of the auth-store module to avoid a circular import.
// The store registers its callbacks during initialization via setAuthBridge().
interface AuthBridge {
  getAccessToken: () => string | null;
  setAccessToken: (token: string) => void;
  onSessionExpired: () => void;
}

let bridge: AuthBridge | null = null;

export function setAuthBridge(next: AuthBridge): void {
  bridge = next;
}

// Read the current access token without going through the axios interceptor.
// Callers on `authClient` (which has no interceptor) use this to opt in to
// sending Authorization on specific requests — e.g. /magic-login/ needs to
// reveal who's already signed in so the backend can reject cross-user swaps.
export function getCurrentAccessToken(): string | null {
  return bridge?.getAccessToken() ?? null;
}

const BASE_CONFIG = {
  baseURL: API_BASE_URL,
  withCredentials: true, // send httpOnly refresh cookie
  headers: { 'Content-Type': 'application/json' },
};

export const authClient: AxiosInstance = axios.create(BASE_CONFIG);
export const apiClient: AxiosInstance = axios.create(BASE_CONFIG);

// Request: attach Bearer access token when available.
apiClient.interceptors.request.use((config) => {
  const token = bridge?.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response: refresh on 401, retry once.
// `refreshPromise` is the lock: all concurrent 401s wait on the same refresh.
//
// `refreshPromise` resolves to one of three outcomes so callers can tell a
// truly-dead session apart from a transient blip:
//   - { ok: true, token }     — refreshed; retry with the new token
//   - { ok: false, expired }  — refresh endpoint returned 401: session is
//                               genuinely gone → force logout
//   - { ok: false, !expired } — network/5xx/CORS: DON'T nuke the session, let
//                               the original error surface as retryable
type RefreshResult = { ok: true; token: string } | { ok: false; sessionExpired: boolean };

let refreshPromise: Promise<RefreshResult> | null = null;

async function doRefresh(): Promise<RefreshResult> {
  try {
    const res = await authClient.post<{ access: string }>('/api/auth/refresh/', {});
    const { access } = res.data;
    bridge?.setAccessToken(access);
    return { ok: true, token: access };
  } catch (err) {
    // Only a real 401 from the refresh endpoint means the session is gone.
    // Network errors, 5xx, CORS, timeouts etc. are transient — surface them
    // as retryable rather than logging the user out.
    const sessionExpired = isAxiosError(err) && err.response?.status === 401;
    return { ok: false, sessionExpired };
  }
}

async function runRefresh(): Promise<RefreshResult> {
  refreshPromise ??= doRefresh().finally(() => {
    refreshPromise = null;
  });
  const result = await refreshPromise;
  if (!result.ok && result.sessionExpired) bridge?.onSessionExpired();
  return result;
}

// Shared entry point for non-axios callers (e.g. the SSE hook, which can't
// go through the response interceptor). Uses the same in-flight lock so
// concurrent callers don't each kick off a refresh. On a genuinely-expired
// session it flips the store to 'unauthed' (via runRefresh) so downstream
// effects tear down on the next render; on transient failures it returns null
// without nuking the session so the caller can retry later.
export async function refreshAccessToken(): Promise<string | null> {
  const result = await runRefresh();
  return result.ok ? result.token : null;
}

// A clean 401 means the server rejected the request *before* processing it
// (the expired access token failed auth), so the request demonstrably never
// mutated state server-side. Replaying it after a successful refresh is
// therefore idempotent in effect — even for POST/PATCH/PUT/DELETE — and avoids
// turning every post-expiry first action (create event, RSVP, mark-read,
// cancel) into a user-visible failure. The `_retried` guard below caps replay
// at one attempt, so there's no risk of an infinite loop or double-submit.
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryableConfig | undefined;
    if (!config || error.response?.status !== 401 || config._retried) {
      throw error;
    }
    config._retried = true;

    const result = await runRefresh();
    // Transient refresh failure (network/5xx) or genuinely-expired session:
    // either way, don't retry — surface the original error. On a real expiry
    // runRefresh already fired onSessionExpired.
    if (!result.ok) throw error;

    // Refresh succeeded and the original 401 proves the request had no side
    // effect, so replay it once with the new token — regardless of method.
    config.headers.Authorization = `Bearer ${result.token}`;
    const retried = await apiClient.request(config);
    return retried;
  },
);
