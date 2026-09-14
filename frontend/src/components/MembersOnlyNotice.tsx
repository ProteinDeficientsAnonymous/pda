import { Link } from 'react-router-dom';

import { ContentContainer } from '@/screens/public/ContentContainer';

/**
 * Shown in place of a members-only screen for a tentatively-approved user.
 * `what` names the thing they're waiting on, e.g. "the member directory".
 */
export function MembersOnlyNotice({ what }: { what: string }) {
  return (
    <ContentContainer>
      <h1 className="mb-3 text-2xl font-medium tracking-tight">not just yet 🌱</h1>
      <p className="text-foreground-secondary text-sm">
        you&rsquo;re tentatively approved — come to an official or club event in person and
        we&rsquo;ll open up {what} along with the rest of the app.
      </p>
      <p className="text-foreground-secondary mt-3 text-sm">
        until then you can browse and rsvp to anything official or club on the calendar.
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
