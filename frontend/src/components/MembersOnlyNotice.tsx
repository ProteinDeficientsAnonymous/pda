import { Link } from 'react-router-dom';

import { ATTENDANCE_RULE } from '@/models/user';
import { ContentContainer } from '@/screens/public/ContentContainer';

/**
 * Shown in place of a members-only screen for a limited user (tentative or
 * attendance-paused). `unlocks` names what full access gets them, e.g.
 * "see the member list".
 */
export function MembersOnlyNotice({
  unlocks,
  attendancePaused,
}: {
  unlocks: string;
  attendancePaused: boolean;
}) {
  return (
    <ContentContainer>
      <h1 className="mb-3 text-2xl font-medium tracking-tight">
        you don&rsquo;t have access to this page yet
      </h1>
      <p className="text-foreground-secondary text-sm">
        {attendancePaused ? (
          <>
            your membership is paused while we wait to see you in person — once you&rsquo;ve been to{' '}
            {ATTENDANCE_RULE.minEvents} official or club events in the last{' '}
            {ATTENDANCE_RULE.windowMonths} months, you&rsquo;ll get full access again and be able to{' '}
            {unlocks}.
          </>
        ) : (
          <>
            you&rsquo;re approved but you have to come in person before we make you a full member!
            once you come to an event you&rsquo;ll be able to {unlocks}.
          </>
        )}
      </p>
      <Link
        to="/calendar"
        className="text-brand-700 hover:text-brand-900 mt-4 inline-block text-sm"
      >
        see what&rsquo;s coming up
      </Link>
    </ContentContainer>
  );
}
