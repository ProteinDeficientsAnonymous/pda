import { format } from 'date-fns';

import type { PreviousArchive, PreviousRejection } from '@/api/join';
import { rejectionReasonText } from '@/api/rejectionEmail';

function formatHistoryDate(iso: string | null): string {
  return iso ? ` on ${format(new Date(iso), 'MMM d, yyyy').toLowerCase()}` : '';
}

export function PreviousArchiveNote({ archive }: { archive: PreviousArchive | null }) {
  if (!archive) return null;
  const who = archive.archivedByName ? ` by ${archive.archivedByName.toLowerCase()}` : '';
  return (
    <p className="bg-warning-subtle text-warning mt-2 rounded-md px-3 py-2 text-xs">
      previously archived{formatHistoryDate(archive.archivedAt)}
      {who}
    </p>
  );
}

export function PreviousRejectionNote({ rejection }: { rejection: PreviousRejection | null }) {
  if (!rejection) return null;
  const who = (rejection.statusChangedByName ?? 'an admin').toLowerCase();
  const when = formatHistoryDate(rejection.statusChangedAt);
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
