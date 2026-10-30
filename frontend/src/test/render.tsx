import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { type InitialEntry, MemoryRouter } from 'react-router-dom';

export function makeQueryClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

export function queryWrapper(qc: QueryClient = makeQueryClient()) {
  return function QueryWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

interface ProviderOptions {
  route?: InitialEntry;
  qc?: QueryClient;
}

export function renderWithProviders(
  ui: ReactElement,
  { route = '/', qc = makeQueryClient() }: ProviderOptions = {},
) {
  function Providers({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  }
  return { qc, ...render(ui, { wrapper: Providers }) };
}
