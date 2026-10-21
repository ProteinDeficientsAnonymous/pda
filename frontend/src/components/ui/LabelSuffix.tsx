import type { ReactNode } from 'react';

/** Secondary note rendered beside a field label, e.g. "· required". */
export function LabelSuffix({ children }: { children: ReactNode }) {
  // the leading space keeps the accessible name readable ("notes · required")
  return (
    <>
      {' '}
      <span className="text-muted text-xs font-normal">{children}</span>
    </>
  );
}
