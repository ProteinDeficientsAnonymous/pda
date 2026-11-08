import { format } from 'date-fns';

import { type RestoredMember, ReturnKind, useRestoredMembers } from '@/api/restoredMembers';
import { formatPhone } from '@/utils/formatPhone';

import { AttendedEventsNote } from './AttendedEventsNote';
import { JoinRequestWhatsappToggle } from './JoinRequestWhatsappToggle';
import { SearchResultsList } from './SearchResultsList';

function matchesQuery(member: RestoredMember, q: string): boolean {
  return member.fullName.toLowerCase().includes(q) || member.phoneNumber.includes(q);
}

const formatDay = (date: Date | null) => (date ? format(date, 'MMM d, yyyy').toLowerCase() : '');

function returnStatus(member: RestoredMember): string {
  if (member.kind === ReturnKind.RESTORED) return `restored ${formatDay(member.restoredAt)}`;
  if (member.cameInPersonAt) return `came in person ${formatDay(member.cameInPersonAt)}`;
  return `unpaused ${formatDay(member.unpausedAt)} · waiting to come in person`;
}

function RestoredMemberCard({ member }: { member: RestoredMember }) {
  return (
    <article className="border-border bg-surface rounded-lg border p-4">
      <h2 className="text-base font-medium">
        {member.fullName || formatPhone(member.phoneNumber)}
      </h2>
      <p className="text-muted text-xs">
        {formatPhone(member.phoneNumber)} · {returnStatus(member)}
      </p>
      <AttendedEventsNote events={member.recentEvents} label="latest qualifying events" />
      <JoinRequestWhatsappToggle userId={member.id} checked={member.hasJoinedWhatsapp} />
    </article>
  );
}

export function RestoredMembersList({ query }: { query: string }) {
  const { data = [], isPending, isError } = useRestoredMembers();

  if (isPending) return <p className="text-muted text-sm">loading…</p>;
  if (isError) {
    return (
      <p role="alert" className="text-destructive text-sm">
        couldn't load restored members — try refreshing
      </p>
    );
  }

  const q = query.trim().toLowerCase();
  const visible = data.filter((m) => matchesQuery(m, q));

  return (
    <SearchResultsList
      query={query}
      items={visible.map((m) => (
        <li key={m.id}>
          <RestoredMemberCard member={m} />
        </li>
      ))}
    />
  );
}
