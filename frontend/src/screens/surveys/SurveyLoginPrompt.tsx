import { Link, useLocation } from 'react-router-dom';

import { ContentContainer } from '@/screens/public/ContentContainer';

function useLoginHref() {
  const location = useLocation();
  return `/login?redirect=${encodeURIComponent(location.pathname + location.search)}`;
}

export function SurveyLoginNotice() {
  const loginHref = useLoginHref();
  return (
    <ContentContainer>
      <section className="border-border bg-surface mt-8 rounded-lg border p-6">
        <h2 className="mb-2 text-base font-medium">log in to see this survey</h2>
        <p className="text-foreground-tertiary mb-4 text-sm">
          this link may go to a members-only survey — sign in to check
        </p>
        <div className="flex flex-wrap gap-3">
          <Link
            to={loginHref}
            className="bg-brand-600 text-brand-on hover:bg-brand-700 inline-flex h-10 items-center rounded-md px-4 text-sm font-medium"
          >
            log in
          </Link>
          <Link
            to="/join"
            className="border-border-strong text-foreground-secondary hover:bg-background inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium"
          >
            request to join
          </Link>
        </div>
      </section>
    </ContentContainer>
  );
}

export function SurveyLoginLink({ anonymous }: { anonymous: boolean }) {
  const loginHref = useLoginHref();
  return (
    <p className="text-foreground-secondary mb-6 text-sm">
      already a member?{' '}
      <Link to={loginHref} className="text-brand-700 hover:text-brand-900 underline">
        log in
      </Link>{' '}
      {anonymous ? '— your answers stay anonymous either way' : 'to answer from your account'}
    </p>
  );
}
