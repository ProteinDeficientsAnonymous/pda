import type { ReactNode } from 'react';

export function JoinRequestResults({ query, items }: { query: string; items: ReactNode[] }) {
  if (items.length === 0) {
    return (
      <p className="text-muted text-sm">
        {query.trim() ? 'nothing matches — try a different search' : 'nothing here 🌿'}
      </p>
    );
  }
  return <ul className="flex flex-col gap-3">{items}</ul>;
}
