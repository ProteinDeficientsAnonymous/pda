import { useMemo, useState } from 'react';

import { useRoles } from '@/api/roles';
import { type Member, useUsers } from '@/api/users';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { BulkCreateDialog } from './BulkCreateDialog';
import { MemberCreateDialog } from './MemberCreateDialog';
import { MemberRow } from './MemberRow';
import { filterAndSort, formatCountText, SORT_OPTIONS, type SortKey } from './membersFilterSort';
import { MembersRoleFilter } from './MembersRoleFilter';

export type MembersMode = 'members' | 'non-members';

export function MembersTab({ mode }: { mode: MembersMode }) {
  const isNonMembers = mode === 'non-members';
  // The list endpoint returns members-only by default and all users when
  // opted in; the non-members tab keeps only the non-members from that set.
  const { data: fetched = [], isPending, isError } = useUsers(isNonMembers);
  const data = useMemo(
    () => (isNonMembers ? fetched.filter((m) => !m.isMember) : fetched),
    [fetched, isNonMembers],
  );
  const { data: allRoles = [] } = useRoles();
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortKey>('name');
  const [selectedRoles, setSelectedRoles] = useState<Set<string>>(() => new Set());
  const [createOpen, setCreateOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);

  const roleNames = useMemo(() => [...allRoles.map((r) => r.name)].sort(), [allRoles]);

  const visible = useMemo(
    () => filterAndSort(data, query, sort, selectedRoles),
    [data, query, sort, selectedRoles],
  );

  const hasFilters = query.trim() !== '' || selectedRoles.size > 0;
  const countText = formatCountText(visible.length, data.length, hasFilters);

  if (isPending) return <ContentLoading />;
  if (isError)
    return (
      <ContentError
        message={
          isNonMembers
            ? "couldn't load non-members — try refreshing"
            : "couldn't load members — try refreshing"
        }
      />
    );

  return (
    <>
      {isNonMembers ? null : (
        <div className="mb-4 flex justify-end gap-2">
          <Button
            variant="secondary"
            onClick={() => {
              setBulkOpen(true);
            }}
          >
            bulk add
          </Button>
          <Button
            onClick={() => {
              setCreateOpen(true);
            }}
          >
            add member
          </Button>
        </div>
      )}

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1">
          <TextField
            label="search"
            placeholder="name, phone, email, or user id"
            value={query}
            maxLength={100}
            onChange={(e) => {
              setQuery(e.target.value);
            }}
          />
        </div>
        <div className="sm:w-48">
          <Select
            label="sort by"
            options={SORT_OPTIONS}
            value={sort}
            onChange={(e) => {
              setSort(e.target.value as SortKey);
            }}
          />
        </div>
        {roleNames.length > 0 ? (
          <div className="sm:w-56">
            <MembersRoleFilter
              roleNames={roleNames}
              selected={selectedRoles}
              onChange={setSelectedRoles}
            />
          </div>
        ) : null}
      </div>

      {data.length > 0 ? (
        <p className="text-foreground-tertiary mb-3 text-sm">{countText}</p>
      ) : null}

      <MembersList
        members={visible}
        selectedRoles={selectedRoles}
        hasAnyMembers={data.length > 0}
        mode={mode}
      />

      {createOpen ? (
        <MemberCreateDialog
          open
          onClose={() => {
            setCreateOpen(false);
          }}
        />
      ) : null}

      {bulkOpen ? (
        <BulkCreateDialog
          open
          onClose={() => {
            setBulkOpen(false);
          }}
        />
      ) : null}
    </>
  );
}

function MembersList({
  members,
  selectedRoles,
  hasAnyMembers,
  mode,
}: {
  members: Member[];
  selectedRoles: Set<string>;
  hasAnyMembers: boolean;
  mode: MembersMode;
}) {
  if (members.length === 0) {
    const emptyLabel = mode === 'non-members' ? 'no non-members yet 🌿' : 'no members yet 🌿';
    return (
      <p className="text-sm text-neutral-500">
        {!hasAnyMembers ? emptyLabel : 'nothing matches — try clearing filters'}
      </p>
    );
  }

  if (selectedRoles.size === 0) {
    return (
      <ul className="flex flex-col gap-2">
        {members.map((m) => (
          <li key={m.id}>
            <MemberRow member={m} />
          </li>
        ))}
      </ul>
    );
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
          <ul className="flex flex-col gap-2">
            {g.members.map((m) => (
              <li key={m.id}>
                <MemberRow member={m} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
