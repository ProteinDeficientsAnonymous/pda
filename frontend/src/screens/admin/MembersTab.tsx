// Members tab body — the actual list/filter/sort/create UI. The outer
// MembersScreen shell just switches between this and the RolesTab.

import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useRoles } from '@/api/roles';
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
          <div className="sm:w-56">
            <RoleFilter
              roleNames={roleNames}
              selected={selectedRoles}
              onChange={setSelectedRoles}
            />
          </div>
        ) : null}
      </div>

      <MembersList
        members={visible}
        selectedRoles={selectedRoles}
        hasAnyMembers={data.length > 0}
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
}: {
  members: Member[];
  selectedRoles: Set<string>;
  hasAnyMembers: boolean;
}) {
  if (members.length === 0) {
    return (
      <p className="text-sm text-neutral-500">
        {!hasAnyMembers ? 'no members yet 🌿' : 'nothing matches — try clearing filters'}
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

function RoleFilter({
  roleNames,
  selected,
  onChange,
}: {
  roleNames: string[];
  selected: Set<string>;
  onChange: (next: Set<string>) => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const summary =
    selected.size === 0
      ? 'all roles'
      : selected.size === 1
        ? [...selected][0]
        : `${String(selected.size)} roles`;

  function toggle(name: string, checked: boolean) {
    const next = new Set(selected);
    if (checked) next.add(name);
    else next.delete(name);
    onChange(next);
  }

  return (
    <div className="relative flex flex-col gap-1" ref={rootRef}>
      <span className="text-foreground text-sm font-medium">filter by role</span>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => {
          setOpen((o) => !o);
        }}
        className="focus:border-brand-500 focus:ring-brand-200 border-border-strong bg-surface flex h-10 w-full items-center justify-between rounded-md border px-3 text-left text-sm transition-colors outline-none focus:ring-2"
      >
        <span className="text-foreground truncate">{summary}</span>
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          className="text-foreground-secondary ml-2 h-4 w-4 shrink-0"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M6 8l4 4 4-4" />
        </svg>
      </button>
      {open ? (
        <div className="border-border-strong bg-surface absolute top-full left-0 z-20 mt-1 w-full rounded-md border p-2 shadow-md">
          <div className="flex max-h-64 flex-col gap-1.5 overflow-y-auto">
            {roleNames.map((name) => (
              <label
                key={name}
                className="hover:bg-surface-dim flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 text-sm"
              >
                <input
                  type="checkbox"
                  checked={selected.has(name)}
                  onChange={(e) => {
                    toggle(name, e.target.checked);
                  }}
                />
                <span>{name}</span>
              </label>
            ))}
          </div>
          {selected.size > 0 ? (
            <button
              type="button"
              className="text-foreground-secondary mt-2 text-xs hover:underline"
              onClick={() => {
                onChange(new Set());
              }}
            >
              clear
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function filterAndSort(
  members: Member[],
  query: string,
  sort: SortKey,
  selectedRoles: Set<string>,
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
  if (selectedRoles.size > 0) {
    result = result.filter((m) => m.roles.some((r) => selectedRoles.has(r.name)));
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
  const initials = (member.displayName || member.phoneNumber).slice(0, 2).toLowerCase();
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
