import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { getApiStatus } from '@/api/apiErrors';
import { usePublicMyRsvps } from '@/api/publicRsvp';
import {
  clearStoredRsvpToken,
  getStoredRsvpToken,
  setStoredRsvpToken,
} from '@/api/rsvpTokenStorage';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { PublicRsvpCard } from './PublicRsvpCard';

const INVALID_TOKEN_COPY = "this link's expired or invalid — rsvp again to get a new one";

export default function PublicRsvpsScreen() {
  const [searchParams] = useSearchParams();
  const urlToken = searchParams.get('token');
  const [storedToken] = useState(() => getStoredRsvpToken());
  const token = urlToken ?? storedToken ?? '';

  useEffect(() => {
    if (urlToken) setStoredRsvpToken(urlToken);
  }, [urlToken]);

  const { data, isPending, isError, error } = usePublicMyRsvps(token);
  const isInvalidToken = isError && getApiStatus(error) === 404;

  useEffect(() => {
    if (isInvalidToken) clearStoredRsvpToken();
  }, [isInvalidToken]);

  // only a 404 means the link is bad; transient failures must not tell the holder to re-rsvp.
  if (!token || isInvalidToken) {
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
      <p className="text-foreground-secondary mb-6 text-sm">{data.user.name}</p>

      {data.rsvps.length === 0 ? (
        <p className="text-foreground-secondary text-sm">
          you don't have any active rsvps right now 🌿
        </p>
      ) : (
        <div className="flex flex-col gap-4">
          {data.rsvps.map((r) => (
            <PublicRsvpCard
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
