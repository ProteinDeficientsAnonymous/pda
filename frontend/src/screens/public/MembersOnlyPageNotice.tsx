import { useLocation } from 'react-router-dom';

import { useAuthStore } from '@/auth/store';
import { ForbiddenNotice } from '@/components/ForbiddenNotice';
import { MembersOnlyNotice } from '@/components/MembersOnlyNotice';
import { isLimited } from '@/models/event';
import { isAttendancePaused } from '@/models/user';

export function MembersOnlyPageNotice({ unlocks }: { unlocks: string }) {
  const user = useAuthStore((s) => s.user);
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  const location = useLocation();

  if (!isAuthed) {
    return (
      <ForbiddenNotice
        message="log in to see this page"
        subtext="this page is for members only"
        loginRedirect={encodeURIComponent(location.pathname + location.search)}
      />
    );
  }
  if (isLimited(user)) {
    return (
      <MembersOnlyNotice
        unlocks={unlocks}
        attendancePaused={user != null && isAttendancePaused(user)}
      />
    );
  }
  return (
    <ForbiddenNotice
      message="this page is for members only"
      subtext="if you think this is a mistake, reach out to an organizer"
    />
  );
}
