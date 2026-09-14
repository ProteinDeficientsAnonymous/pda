/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  // Dev-only auto-login credentials — see src/auth/devLogin.ts.
  readonly VITE_DEV_LOGIN_PHONE?: string;
  readonly VITE_DEV_LOGIN_PASSWORD?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
