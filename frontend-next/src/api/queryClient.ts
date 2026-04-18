import { QueryClient } from '@tanstack/react-query';

// Defaults tuned for PDA's semantics:
//   - 4xx errors are deterministic, don't retry them.
//   - 30s staleTime means nav within the app feels instant; detailed mutations
//     call invalidateQueries explicitly rather than relying on polling.
export const queryClient = new QueryClient({
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
