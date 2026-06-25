import { describe, expect, it } from 'vitest';

import {
  hasAnyAdminPermission,
  hasPermission,
  normalizePermissions,
  Permission,
  type UserLike,
} from './permissions';

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

  it('does not crash on a non-array permissions value (corrupt role data)', () => {
    // Defense-in-depth: if the backend invariant regresses, treat non-array as "no perms".
    const corrupt = (permissions: unknown) =>
      user({ roles: [{ name: 'custom', isDefault: false, permissions } as never] });
    expect(hasPermission(corrupt(null), Permission.TagOfficialEvent)).toBe(false);
    expect(hasPermission(corrupt(undefined), Permission.TagOfficialEvent)).toBe(false);
    expect(hasPermission(corrupt({}), Permission.TagOfficialEvent)).toBe(false);
  });
});

describe('normalizePermissions', () => {
  it('passes through a string array unchanged', () => {
    const perms = [Permission.ManageEvents, Permission.EditFaq];
    expect(normalizePermissions(perms)).toEqual(perms);
  });

  it('coerces non-array values (null, undefined, object) to an empty array', () => {
    expect(normalizePermissions(null)).toEqual([]);
    expect(normalizePermissions(undefined)).toEqual([]);
    // {} violates the declared type — cast to exercise the runtime guard.
    expect(normalizePermissions({} as never)).toEqual([]);
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
