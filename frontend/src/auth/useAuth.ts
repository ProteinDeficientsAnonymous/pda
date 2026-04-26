import { useAuthStore } from './store';
import {
  hasPermission as check,
  hasAnyAdminPermission as checkAdmin,
  type PermissionKey,
} from '@/models/permissions';

export function useHasPermission(key: PermissionKey): boolean {
  return useAuthStore((s) => check(s.user, key));
}

export function useHasAnyAdminPermission(): boolean {
  return useAuthStore((s) => checkAdmin(s.user));
}
