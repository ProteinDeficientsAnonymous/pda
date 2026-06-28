import { MSW_ENABLED } from '@/config/env';

export async function enableMocking(): Promise<void> {
  if (import.meta.env.PROD || !MSW_ENABLED) return;

  const { worker } = await import('./browser');
  await worker.start({
    onUnhandledRequest(request, print) {
      if (new URL(request.url).pathname.startsWith('/api/')) {
        print.warning();
      }
    },
  });
}
