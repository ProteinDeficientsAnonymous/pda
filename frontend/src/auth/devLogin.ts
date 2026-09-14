import { useAuthStore } from './store';

// Dev-only convenience: submits seed credentials from .env.local to the real
// /login/ endpoint at boot. Not an auth bypass — no new backend surface, and
// every gate (consent, onboarding, password reset) still applies. See
// .env.local.example. `import.meta.env.DEV` is statically false under
// `vite build`, so this whole path is dead-code-eliminated from prod.
function devCredentials(): { phoneNumber: string; password: string } | null {
  if (!import.meta.env.DEV) return null;
  const phoneNumber = import.meta.env.VITE_DEV_LOGIN_PHONE;
  const password = import.meta.env.VITE_DEV_LOGIN_PASSWORD;
  if (!phoneNumber || !password) return null;
  return { phoneNumber, password };
}

export function devAutoLoginConfigured(): boolean {
  return devCredentials() !== null;
}

export async function attemptDevAutoLogin(): Promise<void> {
  const credentials = devCredentials();
  if (!credentials) return;
  // Never overrides a real session, and never re-fires after an in-app logout
  // (that leaves status 'unauthed'; this runs once per load from 'idle').
  if (useAuthStore.getState().status === 'authed') return;
  try {
    await useAuthStore.getState().login(credentials.phoneNumber, credentials.password);
  } catch {
    console.warn('[devLogin] auto-login failed — falling back to the login screen');
  }
}
