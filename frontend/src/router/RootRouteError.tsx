import { useEffect } from 'react';
import { isRouteErrorResponse, useLocation, useNavigate, useRouteError } from 'react-router-dom';
import { reportError } from '@/utils/errorReporter';
import { Button } from '@/components/ui/Button';

export function RootRouteError() {
  const error = useRouteError();
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const err =
      error instanceof Error
        ? error
        : new Error(
            isRouteErrorResponse(error)
              ? `${String(error.status)} ${error.statusText}`
              : String(error),
          );
    void reportError(err, location.pathname);
  }, [error, location.pathname]);

  const message = isRouteErrorResponse(error)
    ? `${String(error.status)} ${error.statusText}`.toLowerCase()
    : error instanceof Error
      ? error.message.toLowerCase()
      : 'something went wrong';

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-xl font-medium">something broke 🌿</h1>
      <p className="max-w-md text-center text-sm text-muted">{message}</p>
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
