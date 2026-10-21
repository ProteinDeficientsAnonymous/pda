import { Link } from 'react-router-dom';

import { ContentContainer } from '@/screens/public/ContentContainer';

/**
 * Shown in place of a members-only screen for a tentatively-approved user.
 * `unlocks` names what they get after their first in-person event, e.g.
 * "see the member list".
 */
export function MembersOnlyNotice({ unlocks }: { unlocks: string }) {
  return (
    <ContentContainer>
      <h1 className="mb-3 text-2xl font-medium tracking-tight">
        you don&rsquo;t have access to this page yet
      </h1>
      <p className="text-foreground-secondary text-sm">
        you&rsquo;re approved but you have to come in person before we make you a full member! once
        you come to an event you&rsquo;ll be able to {unlocks}.
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
