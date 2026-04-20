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

import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';
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
let refreshPromise: Promise<string | null> | null = null;

async function doRefresh(): Promise<string | null> {
  try {
    const res = await authClient.post<{ access: string }>('/api/auth/refresh/', {});
    const { access } = res.data;
    bridge?.setAccessToken(access);
    return access;
  } catch {
    return null;
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryableConfig | undefined;
    if (!config || error.response?.status !== 401 || config._retried) {
      throw error;
    }
    config._retried = true;

    refreshPromise ??= doRefresh().finally(() => {
      refreshPromise = null;
    });

    const token = await refreshPromise;
    if (!token) {
      bridge?.onSessionExpired();
      throw error;
    }
    config.headers.Authorization = `Bearer ${token}`;
    const retried = await apiClient.request(config);
    return retried;
  },
);
