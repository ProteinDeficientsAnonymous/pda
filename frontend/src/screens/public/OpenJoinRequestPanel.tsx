import { Link } from 'react-router-dom';

import { JoinRequestStatus, type OpenJoinRequestStatus } from '@/api/join';

import { ContentContainer } from './ContentContainer';

const linkClass =
  'text-foreground-secondary hover:bg-surface-dim mt-2 inline-flex h-10 items-center rounded-md px-4 text-sm';

export function OpenJoinRequestPanel({ status }: { status: OpenJoinRequestStatus }) {
  const tentative = status === JoinRequestStatus.TENTATIVE;
  return (
    <ContentContainer>
      <div role="status" className="flex flex-col items-center gap-4 text-center">
        <div aria-hidden="true" className="text-4xl">
          🌱
        </div>
        <h1 className="text-2xl font-medium tracking-tight">
          {tentative ? "you've already been welcomed in" : 'you already have a request in'}
        </h1>
        <p className="text-foreground-tertiary text-sm">
          {tentative
            ? 'your request was approved — log in with your phone number to get started'
            : "it's waiting for a vetting member to review — no need to send another, we'll reach out soon"}
        </p>
        {tentative ? (
          <Link to="/login" className={linkClass}>
            log in
          </Link>
        ) : (
          <Link to="/" className={linkClass}>
            back to home
          </Link>
        )}
      </div>
    </ContentContainer>
  );
}
