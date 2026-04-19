// Admin: /members — two-tab shell switching between the member list and
// role management. Mirrors the Flutter TabController(length:2) layout.

import { useState } from 'react';
import { useAuthStore } from '@/auth/store';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { Permission, hasPermission } from '@/models/permissions';
import { ContentContainer } from '@/screens/public/ContentContainer';
import { MembersTab } from './MembersTab';
import { RolesTab } from './RolesTab';

type TabKey = 'members' | 'roles';

export default function MembersScreen() {
  const user = useAuthStore((s) => s.user);
  const canManageRoles = hasPermission(user, Permission.ManageRoles);
  const [tab, setTab] = useState<TabKey>('members');

  const tabOptions: { value: TabKey; label: string }[] = canManageRoles
    ? [
        { value: 'members', label: 'members' },
        { value: 'roles', label: 'roles' },
      ]
    : [{ value: 'members', label: 'members' }];

  return (
    <ContentContainer>
      <header className="mb-4">
        <h1 className="mb-3 text-2xl font-medium tracking-tight">members</h1>
        {canManageRoles ? (
          <SegmentedControl
            name="members-tab"
            ariaLabel="members or roles"
            options={tabOptions}
            value={tab}
            onChange={setTab}
          />
        ) : null}
      </header>

      {tab === 'members' || !canManageRoles ? <MembersTab /> : <RolesTab />}
    </ContentContainer>
  );
}
