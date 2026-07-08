import {
  hasAnyAdminPermission as checkAdmin,
  hasPermission as check,
  type PermissionKey,
} from '@/models/permissions';

import { useAuthStore } from './store';

export function useHasPermission(key: PermissionKey): boolean {
  return useAuthStore((s) => check(s.user, key));
}

export function useHasAnyAdminPermission(): boolean {
  return useAuthStore((s) => checkAdmin(s.user));
}
