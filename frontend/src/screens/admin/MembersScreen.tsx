import { useState } from 'react';

import { useAuthStore } from '@/auth/store';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { hasPermission, Permission } from '@/models/permissions';
import { ContentContainer } from '@/screens/public/ContentContainer';

import { type MembersMode, MembersTab } from './MembersTab';
import { RolesTab } from './RolesTab';

type TabKey = MembersMode | 'roles';

export default function MembersScreen() {
  const user = useAuthStore((s) => s.user);
  const canManageRoles = hasPermission(user, Permission.ManageRoles);
  const [tab, setTab] = useState<TabKey>('members');

  const tabOptions: { value: TabKey; label: string }[] = [
    { value: 'members', label: 'members' },
    { value: 'non-members', label: 'non-members' },
    ...(canManageRoles ? [{ value: 'roles' as const, label: 'roles' }] : []),
  ];

  return (
    <ContentContainer>
      <div className="mb-4">
        <SegmentedControl
          name="members-tab"
          ariaLabel="members, non-members, or roles"
          options={tabOptions}
          value={tab}
          onChange={setTab}
        />
      </div>

      {tab === 'roles' ? <RolesTab /> : <MembersTab key={tab} mode={tab} />}
    </ContentContainer>
  );
}
