import '@/auth/store';
import '@/accessibility/store';

import { QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';
import { Toaster } from 'sonner';

import { queryClient } from '@/api/queryClient';
import { router } from '@/router/routes';

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster
        position="top-center"
        richColors
        closeButton
        toastOptions={{
          classNames: {
            toast: 'flex-wrap!',
            actionButton:
              'bg-brand-600! text-brand-on! hover:bg-brand-700! mt-2! ml-0! h-9! w-full! basis-full! rounded-md! px-3! text-sm! font-medium! transition-colors!',
          },
        }}
      />
    </QueryClientProvider>
  );
}
