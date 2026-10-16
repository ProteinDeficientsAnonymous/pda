import { type ComponentType, lazy, type ReactNode, Suspense } from 'react';

function FallbackSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-sm text-neutral-500">loading…</div>
    </div>
  );
}

export function lazyEl(children: ReactNode): ReactNode {
  return <Suspense fallback={<FallbackSpinner />}>{children}</Suspense>;
}

// After a deploy, the tab's cached index.html points to chunk filenames
// that no longer exist on the server. The first dynamic import 404s, so
// we retry once and, on a second failure, hard-reload to pick up the new
// index.html. The sessionStorage flag keeps us from getting stuck in a
// reload loop if the failure is something other than a stale deploy.
const RELOAD_FLAG = 'lazy-reload-attempted';

export function lazyWithRetry<T extends ComponentType<unknown>>(
  factory: () => Promise<{ default: T }>,
): ReturnType<typeof lazy<T>> {
  return lazy(async () => {
    try {
      const mod = await factory();
      sessionStorage.removeItem(RELOAD_FLAG);
      return mod;
    } catch (err) {
      if (!isChunkLoadError(err)) throw err;
      try {
        return await factory();
      } catch (retryErr) {
        if (!isChunkLoadError(retryErr)) throw retryErr;
        if (sessionStorage.getItem(RELOAD_FLAG) === '1') throw retryErr;
        sessionStorage.setItem(RELOAD_FLAG, '1');
        window.location.reload();
        return new Promise<{ default: T }>(() => {
          // Never resolves — reload is in flight; React stays in suspense.
        });
      }
    }
  });
}

// AuthBoot holds every route until the session restores; landing on `path`
// starts its chunk download alongside that instead of after it.
export function preloadOnPath(path: string, factory: () => Promise<unknown>): void {
  if (window.location.pathname.toLowerCase() !== path) return;
  // A failed preload is fine: lazyWithRetry retries when the route renders.
  factory().catch(() => undefined);
}

export function isChunkLoadError(err: unknown): boolean {
  if (!(err instanceof Error)) return false;
  const msg = err.message.toLowerCase();
  return (
    msg.includes('failed to fetch dynamically imported module') ||
    msg.includes('error loading dynamically imported module') ||
    msg.includes('importing a module script failed') ||
    err.name === 'ChunkLoadError'
  );
}
