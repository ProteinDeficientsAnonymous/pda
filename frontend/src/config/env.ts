const rawApiUrl: string = import.meta.env.VITE_API_URL ?? '';

// Normalize: strip trailing slash so route strings ('/api/auth/login/') compose cleanly.
export const API_BASE_URL: string = rawApiUrl.replace(/\/$/, '');
