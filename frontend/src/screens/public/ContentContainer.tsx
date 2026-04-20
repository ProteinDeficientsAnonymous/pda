// Shared prose page container. Centers content at max-w-3xl with vertical
// padding and a consistent empty/loading/error UX.

import type { ReactNode } from 'react';

export function ContentContainer({ children }: { children: ReactNode }) {
  return <main className="mx-auto max-w-3xl px-4 py-8 md:py-12">{children}</main>;
}

export function ContentLoading({ label = 'loading…' }: { label?: string }) {
  return (
    <ContentContainer>
      <p className="text-muted text-sm">{label}</p>
    </ContentContainer>
  );
}

export function ContentError({ message }: { message: string }) {
  return (
    <ContentContainer>
      <p role="alert" className="text-destructive text-sm">
        {message}
      </p>
    </ContentContainer>
  );
}
