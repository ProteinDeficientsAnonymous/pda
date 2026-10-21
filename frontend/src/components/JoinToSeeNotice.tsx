import { Link, useLocation } from 'react-router-dom';

import { ContentContainer } from '@/screens/public/ContentContainer';

export function JoinToSeeNotice() {
  const location = useLocation();
  const redirect = encodeURIComponent(location.pathname + location.search);
  return (
    <ContentContainer>
      <h1 className="mb-3 text-2xl font-medium tracking-tight">you can&rsquo;t see this yet</h1>
      <p className="text-foreground-secondary text-sm">
        this part of pda is just for members. request to join and once you&rsquo;re in you&rsquo;ll
        be able to see member profiles and more.
      </p>
      <Link to="/join" className="text-brand-700 hover:text-brand-900 mt-4 inline-block text-sm">
        request to join
      </Link>
      <Link
        to={`/login?redirect=${redirect}`}
        className="text-brand-700 hover:text-brand-900 mt-2 block text-sm"
      >
        already a member? sign in
      </Link>
    </ContentContainer>
  );
}
