import type { Member } from '@/api/users';

import { isAttendancePaused, isGuidelinesPaused } from './memberPause';

export function PauseBadges({ member }: { member: Pick<Member, 'membershipStatus'> }) {
  return (
    <>
      {isGuidelinesPaused(member) ? <PauseBadge label="paused · guidelines" /> : null}
      {isAttendancePaused(member) ? <PauseBadge label="paused · event rqmt" /> : null}
    </>
  );
}

function PauseBadge({ label }: { label: string }) {
  return (
    <span className="bg-warning-subtle text-warning rounded-full px-2 py-0.5 text-xs">{label}</span>
  );
}
