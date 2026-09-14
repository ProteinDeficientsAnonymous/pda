// Read the key directly off import.meta.env — destructuring or aliasing the whole
// object defeats Vite's per-key static replacement and inlines EVERY VITE_* var
// present at build time into the bundle.
const rawApiUrl: string = import.meta.env.VITE_API_URL ?? '';

// Normalize: strip trailing slash so route strings ('/api/auth/login/') compose cleanly.
export const API_BASE_URL: string = rawApiUrl.replace(/\/$/, '');
