// Permission keys — mirror backend/users/permissions.py PermissionKey.
// Must stay in sync with the Django enum; when adding a key, add it in both places.
export const Permission = {
  ManageUsers: 'manage_users',
  ApproveJoinRequests: 'approve_join_requests',
  ManageEvents: 'manage_events',
  ManageWhatsapp: 'manage_whatsapp',
  EditJoinQuestions: 'edit_join_questions',
  ManageSurveys: 'manage_surveys',
  EditGuidelines: 'edit_guidelines',
  EditFaq: 'edit_faq',
  EditHome: 'edit_home',
  EditDocs: 'edit_docs',
} as const;

export type PermissionKey = (typeof Permission)[keyof typeof Permission];

// Admin roll-up — any permission in this set grants access to the admin hub.
// Mirrors User.hasAnyAdminPermission in Flutter / has_any_admin_permission on backend.
const ADMIN_PERMISSIONS: readonly PermissionKey[] = [
  Permission.ManageUsers,
  Permission.ApproveJoinRequests,
  Permission.ManageEvents,
  Permission.ManageWhatsapp,
  Permission.EditJoinQuestions,
  Permission.ManageSurveys,
];

export interface UserLike {
  isSuperuser: boolean;
  roles: readonly { isDefault: boolean; permissions: readonly string[] }[];
}

export function hasPermission(user: UserLike | null, key: PermissionKey): boolean {
  if (!user) return false;
  if (user.isSuperuser) return true;
  return user.roles.some((role) => role.isDefault || role.permissions.includes(key));
}

export function hasAnyAdminPermission(user: UserLike | null): boolean {
  if (!user) return false;
  if (user.isSuperuser) return true;
  return ADMIN_PERMISSIONS.some((p) => hasPermission(user, p));
}
