import { useSearchParams } from 'react-router-dom';

import { getApiStatus } from '@/api/apiErrors';
import { useMyRsvps } from '@/api/publicRsvp';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { MyRsvpCard } from './MyRsvpCard';

const INVALID_TOKEN_COPY = "this link's expired or invalid — rsvp again to get a new one";

export default function MyRsvpsScreen() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const { data, isPending, isError, error } = useMyRsvps(token);

  // Only a 404 (unresolvable token) means the link is bad; transient failures
  // (429 rate-limit, 5xx, offline) must not tell the holder to re-rsvp.
  if (!token || (isError && getApiStatus(error) === 404)) {
    return (
      <ContentContainer>
        <p className="text-foreground text-base">{INVALID_TOKEN_COPY}</p>
      </ContentContainer>
    );
  }
  if (isError) return <ContentError message="couldn't load your rsvps — try refreshing" />;
  if (isPending) return <ContentLoading label="loading your rsvps…" />;

  return (
    <ContentContainer>
      <h1 className="text-foreground mb-1 text-2xl font-semibold">your rsvps</h1>
      <p className="text-foreground-secondary mb-6 text-sm">{data.user.displayName}</p>

      {data.rsvps.length === 0 ? (
        <p className="text-foreground-secondary text-sm">
          you don't have any active rsvps right now 🌿
        </p>
      ) : (
        <div className="flex flex-col gap-4">
          {data.rsvps.map((r) => (
            <MyRsvpCard
              key={r.event.id}
              token={token}
              event={r.event}
              status={r.status}
              hasPlusOne={r.hasPlusOne}
            />
          ))}
        </div>
      )}
    </ContentContainer>
  );
}
