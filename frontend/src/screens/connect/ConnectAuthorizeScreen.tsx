import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { getApiStatus } from '@/api/apiErrors';
import { useApproveConnect, useConnectRequest, useDenyConnect } from '@/api/connect';
import { Button } from '@/components/ui/Button';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

import { isSafeRedirect } from './isSafeRedirect';

const NOT_FOUND_MESSAGE = "this connection request doesn't exist.";
const UNSAFE_REDIRECT_MESSAGE = "this app's return address isn't allowed";
const FRAMED_MESSAGE = 'for your security, open this page directly in your browser';
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const GENERIC_MESSAGE = 'something went wrong — try again';

const STATUS_MESSAGES: Record<number, string> = {
  404: NOT_FOUND_MESSAGE,
  409: 'this request was already used.',
  410: 'this request expired. go back to your ai app and try connecting again.',
};

function messageForError(err: unknown): string {
  const status = getApiStatus(err);
  return (status === null ? undefined : STATUS_MESSAGES[status]) ?? GENERIC_MESSAGE;
}

export default function ConnectAuthorizeScreen() {
  const [params] = useSearchParams();
  const rawRequestId = params.get('request');
  const framed = window.top !== window.self;
  const requestId =
    !framed && rawRequestId && UUID_PATTERN.test(rawRequestId) ? rawRequestId : null;
  const request = useConnectRequest(requestId);
  const approve = useApproveConnect();
  const deny = useDenyConnect();
  const [error, setError] = useState<string | null>(null);
  const [redirecting, setRedirecting] = useState(false);

  if (framed) return <ContentError message={FRAMED_MESSAGE} />;
  if (!requestId) return <ContentError message={NOT_FOUND_MESSAGE} />;
  if (request.isPending) return <ContentLoading />;
  if (request.isError) return <ContentError message={messageForError(request.error)} />;

  const { clientName, redirectHost } = request.data;
  const busy = approve.isPending || deny.isPending || redirecting;

  function decide(mutation: typeof approve) {
    if (!requestId || busy) return;
    setError(null);
    mutation.mutate(requestId, {
      onSuccess: (redirectUrl) => {
        if (!isSafeRedirect(redirectUrl, redirectHost)) {
          setError(UNSAFE_REDIRECT_MESSAGE);
          return;
        }
        setRedirecting(true);
        window.location.assign(redirectUrl);
      },
      onError: (err) => {
        setError(messageForError(err));
      },
    });
  }

  return (
    <ContentContainer className="max-w-md">
      <div className="border-border bg-surface rounded-lg border p-6 shadow-(--shadow-sm)">
        <h1 className="text-foreground text-xl font-medium tracking-tight">
          {`connect ${clientName} to pda`}
        </h1>
        <p className="text-foreground-secondary mt-4 text-sm">
          {`${clientName} wants to act as you in pda. it will be able to see and do anything your account can, including member info your roles allow. that info will be sent to ${clientName}.`}
        </p>
        <p className="text-foreground-tertiary mt-3 text-xs">
          {`after you allow, you'll be sent to ${redirectHost}`}
        </p>
        {error ? (
          <p role="alert" className="text-destructive mt-4 text-sm">
            {error}
          </p>
        ) : null}
        <div className="mt-6 flex gap-3">
          <Button
            disabled={busy}
            onClick={() => {
              decide(approve);
            }}
          >
            allow
          </Button>
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => {
              decide(deny);
            }}
          >
            deny
          </Button>
        </div>
      </div>
    </ContentContainer>
  );
}
