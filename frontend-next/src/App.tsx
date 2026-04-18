import { QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';
import { Toaster } from 'sonner';
import { queryClient } from '@/api/queryClient';
import { router } from '@/router/routes';
// Side-effect import: registers the axios ↔ store bridge before any request fires.
import '@/auth/store';

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster position="top-center" richColors closeButton />
    </QueryClientProvider>
  );
}
