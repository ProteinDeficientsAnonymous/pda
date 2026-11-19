import { vi } from 'vitest';

export const apiClient = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
};

export const authClient = {
  get: vi.fn(),
  post: vi.fn(),
};

export const setAuthBridge = vi.fn();
export const getCurrentAccessToken = vi.fn();
export const refreshAccessToken = vi.fn();
