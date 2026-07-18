import { MutationCache, QueryClient } from '@tanstack/react-query';

import { reportError } from '@/utils/errorReporter';

// Defaults tuned for PDA's semantics:
//   - 4xx errors are deterministic, don't retry them.
//   - 30s staleTime means nav within the app feels instant; detailed mutations
//     call invalidateQueries explicitly rather than relying on polling.
export const queryClient = new QueryClient({
  // Report-only backstop: log every mutation failure to the backend. No toast —
  // components own user-facing messaging, so toasting here would double-notify.
  mutationCache: new MutationCache({
    onError: (error) => {
      void reportError(error, 'mutation');
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: (failureCount, error) => {
        const status = (error as { response?: { status?: number } }).response?.status;
        if (status !== undefined && status >= 400 && status < 500) return false;
        return failureCount < 2;
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});
