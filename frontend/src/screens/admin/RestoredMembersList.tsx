import { format } from 'date-fns';

import { type RestoredMember, useRestoredMembers } from '@/api/restoredMembers';
import { formatPhone } from '@/utils/formatPhone';

import { AttendedEventsNote } from './AttendedEventsNote';
import { JoinRequestResults } from './JoinRequestResults';
import { JoinRequestWhatsappToggle } from './JoinRequestWhatsappToggle';

function matchesQuery(member: RestoredMember, q: string): boolean {
  return member.fullName.toLowerCase().includes(q) || member.phoneNumber.includes(q);
}

function RestoredMemberCard({ member }: { member: RestoredMember }) {
  return (
    <article className="border-border bg-surface rounded-lg border p-4">
      <h2 className="text-base font-medium">
        {member.fullName || formatPhone(member.phoneNumber)}
      </h2>
      <p className="text-muted text-xs">
        {formatPhone(member.phoneNumber)} · restored{' '}
        {format(member.restoredAt, 'MMM d, yyyy').toLowerCase()}
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
    <JoinRequestResults
      query={query}
      items={visible.map((m) => (
        <li key={m.id}>
          <RestoredMemberCard member={m} />
        </li>
      ))}
    />
  );
}
