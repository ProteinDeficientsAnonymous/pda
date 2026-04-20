import { useEffect } from 'react';
import { isRouteErrorResponse, useLocation, useNavigate, useRouteError } from 'react-router-dom';
import { reportError } from '@/utils/errorReporter';
import { Button } from '@/components/ui/Button';
import { isChunkLoadError } from './lazyRoute';

const CHUNK_RELOAD_FLAG = 'chunk-error-reload-attempted';

export function RootRouteError() {
  const error = useRouteError();
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    // A chunk-load error at this point almost always means the tab is
    // holding a stale index.html after a deploy. Reload once to pick up
    // the fresh asset manifest; the sessionStorage flag prevents a loop
    // if something else (cdn outage, offline) is actually broken.
    if (isChunkLoadError(error) && sessionStorage.getItem(CHUNK_RELOAD_FLAG) !== '1') {
      sessionStorage.setItem(CHUNK_RELOAD_FLAG, '1');
      window.location.reload();
      return;
    }

    const err =
      error instanceof Error
        ? error
        : new Error(
            isRouteErrorResponse(error)
              ? `${String(error.status)} ${error.statusText}`
              : String(error),
          );
    const context: Record<string, unknown> = { boundary: 'RootRouteError' };
    if (isRouteErrorResponse(error)) {
      context.routeErrorStatus = error.status;
      context.routeErrorStatusText = error.statusText;
    }
    void reportError(err, location.pathname, context);
  }, [error, location.pathname]);

  const message = isRouteErrorResponse(error)
    ? `${String(error.status)} ${error.statusText}`.toLowerCase()
    : error instanceof Error
      ? error.message.toLowerCase()
      : 'something went wrong';

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-xl font-medium">something broke 🌿</h1>
      <p className="text-muted max-w-md text-center text-sm">{message}</p>
      <Button
        type="button"
        variant="secondary"
        onClick={() => {
          void navigate('/');
        }}
      >
        back home
      </Button>
    </div>
  );
}
