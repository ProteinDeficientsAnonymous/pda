import { Link } from 'react-router-dom';
import { ContentContainer } from './ContentContainer';

export default function JoinSuccessScreen() {
  return (
    <ContentContainer>
      <div className="flex flex-col items-center gap-4 text-center">
        <div aria-hidden="true" className="text-4xl">
          🌱
        </div>
        <h1 className="text-2xl font-medium tracking-tight">request received!</h1>
        <p className="text-foreground-tertiary text-sm">
          a vetting member will review your request and reach out soon
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
