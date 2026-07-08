import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { axe } from 'vitest-axe';

import InstallAppScreen from './InstallAppScreen';

function renderWith(component: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{component}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('InstallAppScreen accessibility', () => {
  it('has no axe violations', async () => {
    const { container } = renderWith(<InstallAppScreen />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
