import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { getApiStatus } from '@/api/apiErrors';
import { usePublicMyRsvps } from '@/api/publicRsvp';
import {
  clearStoredRsvpToken,
  getStoredRsvpToken,
  setStoredRsvpToken,
} from '@/api/rsvpTokenStorage';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { EventRow } from './EventRow';
import { ResendManageLinkForm } from './ResendManageLinkForm';

const INVALID_TOKEN_COPY = "this link's expired or invalid — rsvp again to get a new one";

export default function PublicRsvpsScreen() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const urlToken = searchParams.get('token');
  const [storedToken] = useState(() => getStoredRsvpToken());
  const token = urlToken ?? storedToken ?? '';
  const [forgetOpen, setForgetOpen] = useState(false);

  useEffect(() => {
    if (urlToken) setStoredRsvpToken(urlToken);
  }, [urlToken]);

  const { data, isPending, isError, error } = usePublicMyRsvps(token);
  const isInvalidToken = isError && getApiStatus(error) === 404;

  useEffect(() => {
    if (isInvalidToken) clearStoredRsvpToken();
  }, [isInvalidToken]);

  function handleForget() {
    clearStoredRsvpToken();
    setForgetOpen(false);
    void navigate('/calendar');
  }

  // only a 404 means the link is bad; transient failures must not tell the holder to re-rsvp.
  if (!token || isInvalidToken) {
    return (
      <ContentContainer>
        <p className="text-foreground text-base">{INVALID_TOKEN_COPY}</p>
        <ResendManageLinkForm />
      </ContentContainer>
    );
  }
  if (isError) return <ContentError message="couldn't load your rsvps — try refreshing" />;
  if (isPending) return <ContentLoading label="loading your rsvps…" />;

  const events = data.rsvps
    .map((r) => r.event)
    .sort(
      (a, b) => (a.startDatetime?.getTime() ?? Infinity) - (b.startDatetime?.getTime() ?? Infinity),
    );

  return (
    <ContentContainer className="pt-4 md:pt-6">
      {events.length === 0 ? (
        <p className="text-muted text-sm">
          nothing coming up 🌿 — events you rsvp to will show up here
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {events.map((e) => (
            <li key={e.id}>
              <EventRow event={e} />
            </li>
          ))}
        </ul>
      )}

      <button
        type="button"
        onClick={() => {
          setForgetOpen(true);
        }}
        className="text-foreground-secondary mt-6 text-sm underline underline-offset-2"
      >
        not you?
      </button>

      <ConfirmDialog
        open={forgetOpen}
        title="not you?"
        message="this'll forget your rsvps on this device — you can always rsvp again to get a new link"
        confirmLabel="forget me"
        cancelLabel="cancel"
        destructive={false}
        onCancel={() => {
          setForgetOpen(false);
        }}
        onConfirm={handleForget}
      />
    </ContentContainer>
  );
}
