// Permission keys — mirror backend/users/permissions.py:PermissionKey.
// Keep in sync: when adding a key, update both sides.
export const Permission = {
  CreateUser: 'create_user',
  ManageUsers: 'manage_users',
  ManageRoles: 'manage_roles',
  ApproveJoinRequests: 'approve_join_requests',
  ManageEvents: 'manage_events',
  EditGuidelines: 'edit_guidelines',
  EditFaq: 'edit_faq',
  EditHomepage: 'edit_homepage',
  EditJoinQuestions: 'edit_join_questions',
  ManageSurveys: 'manage_surveys',
  TagOfficialEvent: 'tag_official_event',
  ManageDocuments: 'manage_documents',
} as const;

export type PermissionKey = (typeof Permission)[keyof typeof Permission];

// The built-in admin role is named "admin". When present as default role,
// it grants every permission. Mirrors user.dart:hasPermission.
export const ADMIN_ROLE_NAME = 'admin';

// Admin roll-up: any of these grants access to /admin. Order matches
// user.dart:hasAnyAdminPermission.
const ADMIN_PERMISSIONS: readonly PermissionKey[] = [
  Permission.ManageEvents,
  Permission.ManageUsers,
  Permission.ApproveJoinRequests,
  Permission.EditJoinQuestions,
  Permission.ManageDocuments,
];

export interface UserLike {
  roles: readonly {
    name: string;
    isDefault: boolean;
    permissions: readonly string[];
  }[];
}

// Backend guarantees permissions: string[] (Role.effective_permissions coerces
// the JSONField). Kept as defense-in-depth so render can't throw if that regresses.
export function normalizePermissions(value: unknown): string[] {
  return Array.isArray(value) ? (value as string[]) : [];
}

export function hasPermission(user: UserLike | null, key: PermissionKey): boolean {
  if (!user) return false;
  // Re-normalize per role: a UserLike can be built in tests or from a source
  // that skipped the API-boundary mapping, so don't assume the invariant holds.
  return user.roles.some(
    (r) =>
      (r.name === ADMIN_ROLE_NAME && r.isDefault) ||
      normalizePermissions(r.permissions).includes(key),
  );
}

export function hasAnyAdminPermission(user: UserLike | null): boolean {
  if (!user) return false;
  return ADMIN_PERMISSIONS.some((p) => hasPermission(user, p));
}
