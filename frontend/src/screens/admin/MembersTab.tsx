// Members tab body — the actual list/filter/sort/create UI. The outer
// MembersScreen shell just switches between this and the RolesTab.

import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useUsers, type Member } from '@/api/users';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { BulkCreateDialog } from './BulkCreateDialog';
import { MemberCreateDialog } from './MemberCreateDialog';

type SortKey = 'name' | 'newest';

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'name', label: 'name (a–z)' },
  { value: 'newest', label: 'newest first' },
];

export function MembersTab() {
  const { data = [], isPending, isError } = useUsers();
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortKey>('name');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [createOpen, setCreateOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);

  const roleNames = useMemo(() => {
    const names = new Set<string>();
    for (const m of data) {
      for (const r of m.roles) names.add(r.name);
    }
    return Array.from(names).sort();
  }, [data]);

  const visible = useMemo(
    () => filterAndSort(data, query, sort, roleFilter),
    [data, query, sort, roleFilter],
  );

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load members — try refreshing" />;

  return (
    <>
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

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1">
          <TextField
            label="search"
            placeholder="name, phone, or email"
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
          <div className="sm:w-48">
            <Select
              label="filter by role"
              options={[
                { value: 'all', label: 'all roles' },
                ...roleNames.map((n) => ({ value: n, label: n })),
              ]}
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
              }}
            />
          </div>
        ) : null}
      </div>

      {visible.length === 0 ? (
        <p className="text-sm text-neutral-500">
          {data.length === 0 ? 'no members yet 🌿' : 'nothing matches — try clearing filters'}
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {visible.map((m) => (
            <li key={m.id}>
              <MemberRow member={m} />
            </li>
          ))}
        </ul>
      )}

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

function filterAndSort(
  members: Member[],
  query: string,
  sort: SortKey,
  roleFilter: string,
): Member[] {
  const q = query.trim().toLowerCase();
  let result = members;
  if (q) {
    result = result.filter(
      (m) =>
        m.displayName.toLowerCase().includes(q) ||
        m.phoneNumber.toLowerCase().includes(q) ||
        m.email.toLowerCase().includes(q),
    );
  }
  if (roleFilter !== 'all') {
    result = result.filter((m) => m.roles.some((r) => r.name === roleFilter));
  }
  const sorted = [...result];
  if (sort === 'name') {
    sorted.sort((a, b) =>
      (a.displayName || a.phoneNumber)
        .toLowerCase()
        .localeCompare((b.displayName || b.phoneNumber).toLowerCase()),
    );
  } else {
    sorted.reverse();
  }
  return sorted;
}

function MemberRow({ member }: { member: Member }) {
  const initials = (member.displayName || member.phoneNumber).slice(0, 2).toUpperCase();
  const primaryRole = member.roles[0]?.name;
  return (
    <Link
      to={`/admin/members/${member.id}`}
      className="flex items-center gap-3 rounded-lg border border-neutral-200 bg-white p-3 transition-colors hover:bg-neutral-50"
    >
      {member.profilePhotoUrl ? (
        <img
          src={member.profilePhotoUrl}
          alt=""
          className="h-10 w-10 shrink-0 rounded-full object-cover"
        />
      ) : (
        <span
          aria-hidden="true"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-neutral-200 text-sm text-neutral-600"
        >
          {initials || '?'}
        </span>
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-neutral-900">
          {member.displayName || member.phoneNumber}
        </p>
        <p className="truncate text-xs text-neutral-500">{member.phoneNumber}</p>
      </div>
      {primaryRole ? (
        <span className="shrink-0 rounded-full bg-neutral-100 px-2 py-0.5 text-xs text-neutral-700">
          {primaryRole}
        </span>
      ) : null}
      {member.isPaused ? (
        <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
          paused
        </span>
      ) : null}
    </Link>
  );
}
