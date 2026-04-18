// Permission keys — mirror backend/users/permissions.py:PermissionKey.
// Keep in sync: when adding a key, update both sides.
export const Permission = {
  CreateUser: 'create_user',
  ManageUsers: 'manage_users',
  ManageRoles: 'manage_roles',
  ApproveJoinRequests: 'approve_join_requests',
  ManageEvents: 'manage_events',
  EditGuidelines: 'edit_guidelines',
  ManageWhatsapp: 'manage_whatsapp',
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
const ADMIN_ROLE_NAME = 'admin';

// Admin roll-up: any of these grants access to /admin. Order matches
// user.dart:hasAnyAdminPermission.
const ADMIN_PERMISSIONS: readonly PermissionKey[] = [
  Permission.ManageEvents,
  Permission.ManageUsers,
  Permission.ApproveJoinRequests,
  Permission.ManageWhatsapp,
  Permission.EditJoinQuestions,
  Permission.ManageDocuments,
];

export interface UserLike {
  isSuperuser: boolean;
  roles: readonly {
    name: string;
    isDefault: boolean;
    permissions: readonly string[];
  }[];
}

export function hasPermission(user: UserLike | null, key: PermissionKey): boolean {
  if (!user) return false;
  if (user.isSuperuser) return true;
  return user.roles.some(
    (r) => (r.name === ADMIN_ROLE_NAME && r.isDefault) || r.permissions.includes(key),
  );
}

export function hasAnyAdminPermission(user: UserLike | null): boolean {
  if (!user) return false;
  if (user.isSuperuser) return true;
  return ADMIN_PERMISSIONS.some((p) => hasPermission(user, p));
}
