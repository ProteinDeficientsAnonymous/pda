import type { ReactNode } from 'react';

export function Card({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="border-border bg-surface rounded-lg border p-4">
      <h2 className="text-muted mb-3 text-xs font-medium tracking-wide">{label}</h2>
      {children}
    </section>
  );
}
