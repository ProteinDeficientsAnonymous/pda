// Placeholder for routes that will be filled in Phases 2–4. Keeps the full
// route tree wired end-to-end during Phase 1 so guards can be exercised.

import { useLocation } from 'react-router-dom';

export default function NotImplemented() {
  const { pathname } = useLocation();
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-2 p-8">
      <h1 className="text-2xl font-medium">coming soon 🌿</h1>
      <p className="text-muted text-sm">this screen is part of a later migration phase</p>
      <code className="bg-surface-dim text-foreground-tertiary rounded px-2 py-1 text-xs">
        {pathname}
      </code>
    </main>
  );
}
