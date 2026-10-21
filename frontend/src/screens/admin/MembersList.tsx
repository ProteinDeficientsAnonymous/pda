import type { Member } from '@/api/users';
import { formatPhone } from '@/utils/formatPhone';

import { MemberRow } from './MemberRow';
import type { MembersMode } from './MembersTab';

export interface MembersSelection {
  selectedIds: Set<string>;
  onToggle: (id: string, checked: boolean) => void;
}

interface Props {
  members: Member[];
  selectedRoles: Set<string>;
  hasAnyMembers: boolean;
  mode: MembersMode;
  selection?: MembersSelection | undefined;
}

export function MembersList({ members, selectedRoles, hasAnyMembers, mode, selection }: Props) {
  if (members.length === 0) {
    const emptyLabel = mode === 'non-members' ? 'no non-members yet 🌿' : 'no members yet 🌿';
    return (
      <p className="text-sm text-neutral-500">
        {!hasAnyMembers ? emptyLabel : 'nothing matches — try clearing filters'}
      </p>
    );
  }

  if (selectedRoles.size === 0) {
    return <MemberItems members={members} selection={selection} />;
  }

  const groups = [...selectedRoles]
    .sort()
    .map((roleName) => ({
      roleName,
      members: members.filter((m) => m.roles.some((r) => r.name === roleName)),
    }))
    .filter((g) => g.members.length > 0);

  return (
    <div className="flex flex-col gap-6">
      {groups.map((g) => (
        <section key={g.roleName}>
          <h2 className="mb-2 text-xs font-medium tracking-wide text-neutral-500">{g.roleName}</h2>
          <MemberItems members={g.members} selection={selection} />
        </section>
      ))}
    </div>
  );
}

function MemberItems({
  members,
  selection,
}: {
  members: Member[];
  selection: MembersSelection | undefined;
}) {
  return (
    <ul className="flex flex-col gap-2">
      {members.map((m) => (
        <li key={m.id} className="flex items-start gap-2">
          {selection ? (
            <input
              type="checkbox"
              aria-label={`select ${(m.fullName || formatPhone(m.phoneNumber)).toLowerCase()}`}
              checked={selection.selectedIds.has(m.id)}
              onChange={(e) => {
                selection.onToggle(m.id, e.target.checked);
              }}
              className="accent-brand-600 mt-4 h-4 w-4 shrink-0 cursor-pointer rounded"
            />
          ) : null}
          <div className="min-w-0 flex-1">
            <MemberRow member={m} />
          </div>
        </li>
      ))}
    </ul>
  );
}
