// Members tab body — the actual list/filter/sort/create UI. Shared between the
// members and non-members tabs (parameterized by `mode`); the outer
// MembersScreen shell switches between this and the RolesTab.

import { format } from 'date-fns';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import { useRoles } from '@/api/roles';
import { type Member, useUsers } from '@/api/users';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { ContentError, ContentLoading } from '@/screens/public/ContentContainer';
import { formatPhone } from '@/utils/formatPhone';

import { BulkCreateDialog } from './BulkCreateDialog';
import { MemberCreateDialog } from './MemberCreateDialog';

export type MembersMode = 'members' | 'non-members';

type SortKey = 'name' | 'newest' | 'lastAttended';

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'name', label: 'name (a–z)' },
  { value: 'newest', label: 'newest first' },
  { value: 'lastAttended', label: 'last attended' },
];

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
            <RoleFilter
              roleNames={roleNames}
              selected={selectedRoles}
              onChange={setSelectedRoles}
            />
          </div>
        ) : null}
      </div>

      {data.length > 0 ? (
        <p className="text-foreground-tertiary mb-3 text-sm">
          {data.length === 1 ? '1 user' : `${String(data.length)} users`}
        </p>
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
                  className="accent-brand-600 h-4 w-4 cursor-pointer rounded"
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
        m.fullName.toLowerCase().includes(q) ||
        m.phoneNumber.toLowerCase().includes(q) ||
        m.email.toLowerCase().includes(q) ||
        m.id.toLowerCase().startsWith(q),
    );
  }
  if (selectedRoles.size > 0) {
    result = result.filter((m) => m.roles.some((r) => selectedRoles.has(r.name)));
  }
  return sortMembers(result, sort);
}

function sortMembers(members: Member[], sort: SortKey): Member[] {
  const sorted = [...members];
  if (sort === 'name') {
    sorted.sort((a, b) =>
      (a.fullName || a.phoneNumber)
        .toLowerCase()
        .localeCompare((b.fullName || b.phoneNumber).toLowerCase()),
    );
    return sorted;
  }
  if (sort === 'lastAttended') {
    // Most recent attendance first; members who never attended sink to the bottom.
    sorted.sort((a, b) => (b.lastAttendedAt?.getTime() ?? 0) - (a.lastAttendedAt?.getTime() ?? 0));
    return sorted;
  }
  // 'newest' — the list arrives oldest-first (phone_number order ≈ creation),
  // so reverse approximates newest-first, matching the prior behavior.
  return sorted.reverse();
}

function MemberRow({ member }: { member: Member }) {
  const initials = (member.fullName || member.phoneNumber).slice(0, 2).toLowerCase();

  // Non-members have no detail page, so the row is a plain div, not a link.
  if (!member.isMember) {
    return (
      <div className="border-border bg-surface flex flex-col gap-2 rounded-lg border p-3">
        <MemberRowBody member={member} initials={initials} />
      </div>
    );
  }

  return (
    <Link
      to={`/admin/members/${member.id}`}
      className="border-border bg-surface hover:bg-surface-dim flex flex-col gap-2 rounded-lg border p-3 transition-colors"
    >
      <MemberRowBody member={member} initials={initials} />
    </Link>
  );
}

function MemberRowBody({ member, initials }: { member: Member; initials: string }) {
  const hasTags = !member.isMember || member.roles.length > 0 || member.isPaused;
  return (
    <>
      <div className="flex items-center gap-3">
        {member.profilePhotoUrl ? (
          <img
            src={member.profilePhotoUrl}
            alt=""
            className="h-10 w-10 shrink-0 rounded-full object-cover"
          />
        ) : (
          <span
            aria-hidden="true"
            className="bg-surface-dim text-foreground-secondary flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm"
          >
            {initials || '?'}
          </span>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-foreground truncate text-sm font-medium">
            {member.fullName || formatPhone(member.phoneNumber)}
          </p>
          <p className="text-foreground-tertiary truncate text-xs">
            {formatPhone(member.phoneNumber)}
          </p>
          {member.email ? (
            <p className="text-foreground-tertiary truncate text-xs">
              {member.email.toLowerCase()}
            </p>
          ) : (
            <p className="text-foreground-tertiary/60 truncate text-xs italic">no email</p>
          )}
          <p className="text-foreground-tertiary/80 truncate text-xs">
            {member.lastAttendedAt
              ? `last attended ${format(member.lastAttendedAt, 'MMM d, yyyy').toLowerCase()}`
              : 'never attended'}
          </p>
        </div>
      </div>
      {hasTags ? (
        <div className="flex flex-wrap gap-1 pl-13">
          {member.roles.map((role) => (
            <span
              key={role.id}
              className="bg-surface-dim text-foreground-secondary rounded-full px-2 py-0.5 text-xs"
            >
              {role.name}
            </span>
          ))}
          {member.isPaused ? (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
              paused
            </span>
          ) : null}
          {!member.isMember ? (
            <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs text-sky-800 dark:bg-sky-900/40 dark:text-sky-200">
              non-member
            </span>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
