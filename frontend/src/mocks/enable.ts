// Mock-mode entrypoint. The `import.meta.env.PROD` guard is statically inlined,
// so Vite folds this branch — and the `./browser` dynamic import — out of prod
// bundles entirely. MSW_ENABLED (VITE_ENABLE_MSW) gates it at runtime in dev.
//
// The notification SSE stream is deliberately unmocked: it's a native
// EventSource the service worker can't intercept, so the bell falls back to
// polling the (mocked) unread-count endpoint.

import { MSW_ENABLED } from '@/config/env';

export async function enableMocking(): Promise<void> {
  if (import.meta.env.PROD || !MSW_ENABLED) return;

  const { worker } = await import('./browser');
  await worker.start({
    // Warn only on unmocked API calls — the signal a screen needs a handler.
    // App assets (JS/CSS/fonts) pass through quietly.
    onUnhandledRequest(request, print) {
      if (new URL(request.url).pathname.startsWith('/api/')) {
        print.warning();
      }
    },
  });
}
