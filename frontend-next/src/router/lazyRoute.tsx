import { Suspense, type ReactNode } from 'react';

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
