const STORAGE_KEY = 'pda-rsvp-token';

export function getStoredRsvpToken(): string | null {
  return localStorage.getItem(STORAGE_KEY);
}

export function setStoredRsvpToken(token: string): void {
  localStorage.setItem(STORAGE_KEY, token);
}

export function clearStoredRsvpToken(): void {
  localStorage.removeItem(STORAGE_KEY);
}
