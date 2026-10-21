import type { Member } from '@/api/users';

export type SortKey = 'name' | 'newest' | 'lastAttended';

export type StatusFilter = 'neverAttended' | 'notInWhatsapp';

export const STATUS_FILTER_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: 'neverAttended', label: 'never attended an event' },
  { value: 'notInWhatsapp', label: 'not in whatsapp' },
];

const STATUS_PREDICATES: Record<StatusFilter, (member: Member) => boolean> = {
  neverAttended: (m) => m.lastAttendedAt === null,
  notInWhatsapp: (m) => !m.hasJoinedWhatsapp,
};

export const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'name', label: 'name (a–z)' },
  { value: 'newest', label: 'newest first' },
  { value: 'lastAttended', label: 'last attended' },
];

export function formatCountText(
  visibleCount: number,
  totalCount: number,
  hasFilters: boolean,
): string {
  if (hasFilters) {
    return `${String(visibleCount)} of ${String(totalCount)} ${totalCount === 1 ? 'user' : 'users'}`;
  }
  return visibleCount === 1 ? '1 user' : `${String(visibleCount)} users`;
}

export function filterAndSort(
  members: Member[],
  query: string,
  sort: SortKey,
  selectedRoles: Set<string>,
  selectedStatuses = new Set<StatusFilter>(),
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
  if (selectedStatuses.size > 0) {
    result = result.filter((m) => [...selectedStatuses].every((s) => STATUS_PREDICATES[s](m)));
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
  sorted.sort((a, b) => b.dateJoined.getTime() - a.dateJoined.getTime());
  return sorted;
}
