import { Link } from 'react-router-dom';

import { ContentContainer } from './ContentContainer';

export function PendingJoinRequestPanel() {
  return (
    <ContentContainer>
      <div role="status" className="flex flex-col items-center gap-4 text-center">
        <div aria-hidden="true" className="text-4xl">
          🌱
        </div>
        <h1 className="text-2xl font-medium tracking-tight">you already requested to join!</h1>
        <p className="text-foreground-tertiary text-sm">
          we're reviewing requests and will get back to you soon
        </p>
        <Link
          to="/"
          className="text-foreground-secondary hover:bg-surface-dim mt-2 inline-flex h-10 items-center rounded-md px-4 text-sm"
        >
          back to home
        </Link>
      </div>
    </ContentContainer>
  );
}
