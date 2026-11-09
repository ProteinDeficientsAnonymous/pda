import { format } from 'date-fns';

import type { PreviousRejection } from '@/api/join';
import { rejectionReasonText } from '@/api/rejectionEmail';

export function PreviousRejectionNote({ rejection }: { rejection: PreviousRejection | null }) {
  if (!rejection) return null;
  const who = (rejection.statusChangedByName ?? 'an admin').toLowerCase();
  const when = rejection.statusChangedAt
    ? ` on ${format(new Date(rejection.statusChangedAt), 'MMM d, yyyy').toLowerCase()}`
    : '';
  const reason = rejectionReasonText(rejection.rejectionReason, rejection.rejectionNote);
  return (
    <div className="bg-warning-subtle text-warning mt-2 rounded-md px-3 py-2 text-xs">
      <p>
        previously rejected by {who}
        {when}
      </p>
      {reason ? <p className="mt-1 whitespace-pre-wrap">reason: {reason}</p> : null}
    </div>
  );
}
