import { describe, it, expect } from 'vitest';
import { Permission, hasPermission, hasAnyAdminPermission, type UserLike } from './permissions';

function user(opts: Partial<UserLike> = {}): UserLike {
  return {
    roles: [],
    ...opts,
  };
}

describe('hasPermission', () => {
  it('returns false for null user', () => {
    expect(hasPermission(null, Permission.ManageUsers)).toBe(false);
  });

  it('default-admin role grants everything', () => {
    const u = user({ roles: [{ name: 'admin', isDefault: true, permissions: [] }] });
    expect(hasPermission(u, Permission.ManageUsers)).toBe(true);
    expect(hasPermission(u, Permission.EditFaq)).toBe(true);
  });

  it('specific permission in role', () => {
    const u = user({
      roles: [{ name: 'custom', isDefault: false, permissions: [Permission.ManageEvents] }],
    });
    expect(hasPermission(u, Permission.ManageEvents)).toBe(true);
    expect(hasPermission(u, Permission.ManageUsers)).toBe(false);
  });

  it('denies when role lacks permission', () => {
    const u = user({ roles: [{ name: 'custom', isDefault: false, permissions: [] }] });
    expect(hasPermission(u, Permission.ManageUsers)).toBe(false);
  });

  it('isDefault without name=admin does not grant blanket access', () => {
    const u = user({ roles: [{ name: 'member', isDefault: true, permissions: [] }] });
    expect(hasPermission(u, Permission.ManageUsers)).toBe(false);
  });
});

describe('hasAnyAdminPermission', () => {
  it('false for null and plain user', () => {
    expect(hasAnyAdminPermission(null)).toBe(false);
    expect(hasAnyAdminPermission(user())).toBe(false);
  });

  it('any admin permission in the set returns true', () => {
    const u = user({
      roles: [{ name: 'custom', isDefault: false, permissions: [Permission.ApproveJoinRequests] }],
    });
    expect(hasAnyAdminPermission(u)).toBe(true);
  });

  it('non-admin permission alone does not qualify', () => {
    const u = user({
      roles: [{ name: 'custom', isDefault: false, permissions: [Permission.EditFaq] }],
    });
    expect(hasAnyAdminPermission(u)).toBe(false);
  });
});
