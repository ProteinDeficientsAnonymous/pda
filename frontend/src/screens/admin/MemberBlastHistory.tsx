import { format } from 'date-fns';

import type { MemberBlast } from '@/api/memberBlast';

export function MemberBlastHistory({ blasts }: { blasts: MemberBlast[] }) {
  if (blasts.length === 0) return null;
  return (
    <section className="mt-8">
      <h2 className="text-lg font-medium">history</h2>
      <ul className="divide-border divide-y">
        {blasts.map((b) => (
          <li key={b.id} className="flex justify-between gap-3 py-2 text-sm">
            <span>{b.subject}</span>
            <span className="text-muted">
              {b.status} · {format(new Date(b.created_at), 'MMM d, yyyy').toLowerCase()}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
