import { format } from 'date-fns';

import type { PreviousArchive, PreviousRejection } from '@/api/join';
import { rejectionReasonText } from '@/api/rejectionEmail';
import { MembershipStatus, type MembershipStatusValue } from '@/models/user';

function formatHistoryDate(iso: string | null): string {
  return iso ? ` on ${format(new Date(iso), 'MMM d, yyyy').toLowerCase()}` : '';
}

const ARCHIVED_WHILE: Partial<Record<MembershipStatusValue, string>> = {
  [MembershipStatus.GuidelinesPaused]: ' while guidelines-paused',
  [MembershipStatus.AttendancePaused]: ' while event rqmt paused',
};

export function PreviousArchiveNote({ archive }: { archive: PreviousArchive | null }) {
  if (!archive) return null;
  const who = archive.archivedByName ? ` by ${archive.archivedByName.toLowerCase()}` : '';
  const pause = archive.pausedStatus ? (ARCHIVED_WHILE[archive.pausedStatus] ?? '') : '';
  return (
    <p className="bg-warning-subtle text-warning mt-2 rounded-md px-3 py-2 text-xs">
      previously archived{formatHistoryDate(archive.archivedAt)}
      {who}
      {pause}
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
