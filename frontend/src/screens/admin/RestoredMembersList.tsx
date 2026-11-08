import { format } from 'date-fns';

import { type RestoredMember, useRestoredMembers } from '@/api/restoredMembers';
import { formatPhone } from '@/utils/formatPhone';

import { JoinRequestResults } from './JoinRequestResults';
import { JoinRequestWhatsappToggle } from './JoinRequestWhatsappToggle';

function formatDay(iso: string): string {
  return format(new Date(iso), 'MMM d, yyyy').toLowerCase();
}

function matchesQuery(member: RestoredMember, q: string): boolean {
  return member.full_name.toLowerCase().includes(q) || member.phone_number.includes(q);
}

function RestoredMemberCard({ member }: { member: RestoredMember }) {
  return (
    <article className="border-border bg-surface rounded-lg border p-4">
      <h2 className="text-base font-medium">
        {member.full_name || formatPhone(member.phone_number)}
      </h2>
      <p className="text-muted text-xs">
        {formatPhone(member.phone_number)} · restored {formatDay(member.restored_at)}
      </p>
      {member.recent_events.length > 0 ? (
        <ul className="text-muted mt-2 text-xs">
          {member.recent_events.map((e) => (
            <li key={e.event_id}>
              {e.title} · {formatDay(e.start_datetime)}
            </li>
          ))}
        </ul>
      ) : null}
      <JoinRequestWhatsappToggle userId={member.id} checked={member.has_joined_whatsapp} />
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
