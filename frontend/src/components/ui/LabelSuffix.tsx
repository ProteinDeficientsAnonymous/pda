import type { ReactNode } from 'react';

/** Secondary note rendered beside a field label, e.g. required/optional. */
export function LabelSuffix({ children }: { children: ReactNode }) {
  // the leading space keeps the accessible name readable ("notes required")
  return (
    <>
      {' '}
      <span className="text-muted-foreground text-xs font-normal">{children}</span>
    </>
  );
}
