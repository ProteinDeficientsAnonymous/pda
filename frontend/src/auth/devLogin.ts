import { useAuthStore } from './store';

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
  // An in-app logout sticks: this only fires from the 'idle' boot path.
  if (useAuthStore.getState().status === 'authed') return;
  try {
    await useAuthStore.getState().login(credentials.phoneNumber, credentials.password);
  } catch {
    console.warn('[devLogin] auto-login failed — falling back to the login screen');
  }
}
