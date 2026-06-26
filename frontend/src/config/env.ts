// Compile-time env. Mirrors the Flutter `String.fromEnvironment('API_URL')` pattern.
// Empty string in prod = same-origin; set to http://localhost:8000 for dev.
const env = import.meta.env as { VITE_API_URL?: string; VITE_ENABLE_MSW?: string };
const rawApiUrl: string = env.VITE_API_URL ?? '';

// Normalize: strip trailing slash so route strings ('/api/auth/login/') compose cleanly.
export const API_BASE_URL: string = rawApiUrl.replace(/\/$/, '');

// When VITE_ENABLE_MSW=true the app starts the MSW worker before rendering and
// serves canned data, running standalone with no backend. Off in prod builds.
export const MSW_ENABLED: boolean = env.VITE_ENABLE_MSW === 'true';
