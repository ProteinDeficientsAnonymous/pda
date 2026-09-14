import { useMemo, useState } from 'react';

import { useRoles } from '@/api/roles';
import { useUsers } from '@/api/users';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { hasPermission, Permission } from '@/models/permissions';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { BulkCreateDialog } from './BulkCreateDialog';
import { MarkAttendedDialog } from './MarkAttendedDialog';
import { MemberCreateDialog } from './MemberCreateDialog';
import { filterAndSort, formatCountText, SORT_OPTIONS, type SortKey } from './membersFilterSort';
import { MembersList } from './MembersList';
import { MembersRoleFilter } from './MembersRoleFilter';
import { MembersSelectionBar } from './MembersSelectionBar';

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
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [markOpen, setMarkOpen] = useState(false);
  const canMarkAttendance = hasPermission(
    useAuthStore((s) => s.user),
    Permission.ManageUsers,
  );

  const roleNames = useMemo(() => [...allRoles.map((r) => r.name)].sort(), [allRoles]);

  const visible = useMemo(
    () => filterAndSort(data, query, sort, selectedRoles),
    [data, query, sort, selectedRoles],
  );

  const hasFilters = query.trim() !== '' || selectedRoles.size > 0;
  const countText = formatCountText(visible.length, data.length, hasFilters);
  const selectedMembers = useMemo(
    () => data.filter((m) => selectedIds.has(m.id)),
    [data, selectedIds],
  );

  function toggleSelected(id: string, checked: boolean) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  function clearSelection() {
    setSelectedIds(new Set());
  }

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

      {canMarkAttendance ? (
        <MembersSelectionBar
          count={selectedMembers.length}
          onMark={() => {
            setMarkOpen(true);
          }}
          onClear={clearSelection}
        />
      ) : null}

      <MembersList
        members={visible}
        selectedRoles={selectedRoles}
        hasAnyMembers={data.length > 0}
        mode={mode}
        selection={canMarkAttendance ? { selectedIds, onToggle: toggleSelected } : undefined}
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

      {markOpen ? (
        <MarkAttendedDialog
          open
          members={selectedMembers}
          onClose={() => {
            setMarkOpen(false);
          }}
          onMarked={() => {
            setMarkOpen(false);
            clearSelection();
          }}
        />
      ) : null}
    </>
  );
}
