// Dialog to create or edit a role. Shows the role name input and a
// checkbox grid of every permission key. Protected roles (admin/member)
// have their name locked but permissions still editable per backend
// rules in users/_roles.py.

import { useState, type SyntheticEvent } from 'react';
import { isAxiosError } from 'axios';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { TextField } from '@/components/ui/TextField';
import { Permission } from '@/models/permissions';
import {
  useCreateRole,
  useUpdateRole,
  type Role,
} from '@/api/roles';

interface Props {
  open: boolean;
  onClose: () => void;
  initialRole: Role | null; // null = create, Role = edit
}

const PERMISSION_LABELS: Record<string, string> = {
  [Permission.CreateUser]: 'create users',
  [Permission.ManageUsers]: 'manage users',
  [Permission.ManageRoles]: 'manage roles',
  [Permission.ApproveJoinRequests]: 'approve join requests',
  [Permission.ManageEvents]: 'manage events',
  [Permission.EditGuidelines]: 'edit guidelines',
  [Permission.ManageWhatsapp]: 'manage whatsapp',
  [Permission.EditFaq]: 'edit faq',
  [Permission.EditHomepage]: 'edit homepage',
  [Permission.EditJoinQuestions]: 'edit join questions',
  [Permission.ManageSurveys]: 'manage surveys',
  [Permission.TagOfficialEvent]: 'tag official events',
  [Permission.ManageDocuments]: 'manage documents',
};

const PROTECTED_ROLE_NAMES = new Set(['admin', 'member']);

export function RoleFormDialog({ open, onClose, initialRole: role }: Props) {
  const isEdit = role !== null;
  const createRole = useCreateRole();
  const updateRole = useUpdateRole(role?.id ?? '');
  const pending = createRole.isPending || updateRole.isPending;

  const [name, setName] = useState(role?.name ?? '');
  const [permissions, setPermissions] = useState<string[]>(role?.permissions ?? []);
  const [formError, setFormError] = useState<string | null>(null);

  function toggle(key: string) {
    setPermissions((prev) =>
      prev.includes(key) ? prev.filter((p) => p !== key) : [...prev, key],
    );
  }

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setFormError(null);
    const trimmedName = name.trim();
    if (!trimmedName) {
      setFormError('role name is required');
      return;
    }
    try {
      if (role) {
        const input: { name?: string; permissions: string[] } = { permissions };
        if (!PROTECTED_ROLE_NAMES.has(role.name)) input.name = trimmedName;
        await updateRole.mutateAsync(input);
      } else {
        await createRole.mutateAsync({ name: trimmedName, permissions });
      }
      onClose();
    } catch (err) {
      if (isAxiosError(err)) {
        const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
        setFormError(detail ?? 'something went wrong — try again');
        return;
      }
      setFormError('something went wrong — try again');
    }
  }

  const nameLocked = role !== null && PROTECTED_ROLE_NAMES.has(role.name);

  return (
    <Dialog open={open} onClose={onClose} title={isEdit ? 'edit role' : 'create role'}>
      <form
        onSubmit={(e) => {
          void onSubmit(e);
        }}
        className="flex flex-col gap-4"
      >
        <TextField
          label="name"
          value={name}
          maxLength={40}
          disabled={nameLocked}
          placeholder="e.g. greeter"
          onChange={(e) => {
            setName(e.target.value);
          }}
        />
        {nameLocked ? (
          <p className="-mt-2 text-xs text-neutral-500">
            built-in role — name is locked
          </p>
        ) : null}

        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-sm font-medium">permissions</legend>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {Object.entries(PERMISSION_LABELS).map(([key, label]) => (
              <label
                key={key}
                className="flex items-center gap-2 text-sm text-neutral-700"
              >
                <input
                  type="checkbox"
                  checked={permissions.includes(key)}
                  onChange={() => {
                    toggle(key);
                  }}
                />
                {label}
              </label>
            ))}
          </div>
        </fieldset>

        {formError ? (
          <p role="alert" className="text-sm text-red-600">
            {formError}
          </p>
        ) : null}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={pending}>
            cancel
          </Button>
          <Button type="submit" disabled={pending}>
            {pending ? 'saving…' : isEdit ? 'save' : 'create'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
