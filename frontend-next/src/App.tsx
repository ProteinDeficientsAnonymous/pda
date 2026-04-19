import { QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';
import { Toaster } from 'sonner';
import { queryClient } from '@/api/queryClient';
import { router } from '@/router/routes';
// Side-effect import: registers the axios ↔ store bridge before any request fires.
import '@/auth/store';
// Side-effect import: applies persisted accessibility prefs to <html> on boot.
import '@/auth/accessibilityStore';

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster position="top-center" richColors closeButton />
    </QueryClientProvider>
  );
}
