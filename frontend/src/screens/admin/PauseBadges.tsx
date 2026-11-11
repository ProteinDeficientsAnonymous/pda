import type { Member } from '@/api/users';

import { isAttendancePaused, isTentative } from './memberPause';

export function PauseBadges({
  member,
}: {
  member: Pick<Member, 'isPaused' | 'attendancePausedAt' | 'membershipStatus'>;
}) {
  return (
    <>
      {member.isPaused ? <PauseBadge label="paused · guidelines" /> : null}
      {isAttendancePaused(member) ? <PauseBadge label="paused · event rqmt" /> : null}
      {isTentative(member) ? (
        <span className="bg-highlight-subtle text-highlight rounded-full px-2 py-0.5 text-xs">
          tentative
        </span>
      ) : null}
    </>
  );
}

function PauseBadge({ label }: { label: string }) {
  return (
    <span className="bg-warning-subtle text-warning rounded-full px-2 py-0.5 text-xs">{label}</span>
  );
}
