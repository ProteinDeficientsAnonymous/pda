// Roles tab body — list existing roles, create new ones, edit permissions,
// or delete. Protected roles (admin/member) can be edited but not deleted.

import { useState } from 'react';
import { isAxiosError } from 'axios';
import { toast } from 'sonner';
import { useDeleteRole, useRoles, type Role } from '@/api/roles';
import { Button } from '@/components/ui/Button';
import { useConfirm } from '@/components/ui/useConfirm';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { RoleFormDialog } from './RoleFormDialog';

const PROTECTED_ROLE_NAMES = new Set(['admin', 'member']);

export function RolesTab() {
  const { data = [], isPending, isError } = useRoles();
  const deleteRole = useDeleteRole();
  const [editing, setEditing] = useState<Role | null>(null);
  const [creating, setCreating] = useState(false);
  const { confirm, element: confirmElement } = useConfirm();

  async function onDelete(role: Role) {
    if (PROTECTED_ROLE_NAMES.has(role.name)) return;
    const warning =
      role.userCount > 0
        ? `${String(role.userCount)} member${role.userCount === 1 ? ' has' : 's have'} the "${role.name}" role — deleting will remove it from ${role.userCount === 1 ? 'them' : 'all of them'}. continue?`
        : `delete the "${role.name}" role? this cannot be undone.`;
    const confirmed = await confirm({
      title: 'delete role',
      message: warning,
      confirmLabel: 'delete',
      destructive: true,
    });
    if (!confirmed) return;
    try {
      await deleteRole.mutateAsync(role.id);
      toast.success(`${role.name} deleted ✓`);
    } catch (err) {
      if (isAxiosError(err)) {
        const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
        toast.error(detail ?? "couldn't delete role — try again");
        return;
      }
      toast.error("couldn't delete role — try again");
    }
  }

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load roles — try refreshing" />;

  return (
    <>
      <div className="mb-4 flex justify-end">
        <Button
          onClick={() => {
            setCreating(true);
          }}
        >
          add role
        </Button>
      </div>

      {data.length === 0 ? (
        <p className="text-sm text-neutral-500">no roles yet 🌿</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {data.map((role) => (
            <li
              key={role.id}
              className="flex items-center justify-between gap-3 rounded-lg border border-neutral-200 bg-white p-3"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-neutral-900">{role.name}</p>
                <p className="truncate text-xs text-neutral-500">
                  {role.permissions.length === 0
                    ? 'no permissions'
                    : `${String(role.permissions.length)} permission${role.permissions.length === 1 ? '' : 's'}`}
                  {' · '}
                  {role.userCount === 0
                    ? 'no members'
                    : `${String(role.userCount)} member${role.userCount === 1 ? '' : 's'}`}
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setEditing(role);
                  }}
                >
                  {role.isDefault ? 'view' : 'edit'}
                </Button>
                {PROTECTED_ROLE_NAMES.has(role.name) ? null : (
                  <Button
                    variant="ghost"
                    onClick={() => {
                      void onDelete(role);
                    }}
                    disabled={deleteRole.isPending}
                  >
                    delete
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {creating ? (
        <RoleFormDialog
          open
          initialRole={null}
          onClose={() => {
            setCreating(false);
          }}
        />
      ) : null}

      {editing ? (
        <RoleFormDialog
          open
          initialRole={editing}
          onClose={() => {
            setEditing(null);
          }}
        />
      ) : null}

      {confirmElement}
    </>
  );
}
