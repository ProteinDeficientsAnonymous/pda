import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';

vi.mock('@/api/join', () => ({
  useJoinQuestions: vi.fn(),
  useSubmitJoinRequest: vi.fn(),
  AlreadyInvitedError: class AlreadyInvitedError extends Error {
    constructor() {
      super('already_invited');
      this.name = 'AlreadyInvitedError';
    }
  },
}));

import JoinScreen from './JoinScreen';
import { useJoinQuestions, useSubmitJoinRequest } from '@/api/join';

const mockUseJoinQuestions = vi.mocked(useJoinQuestions);
const mockUseSubmitJoinRequest = vi.mocked(useSubmitJoinRequest);

function renderWith(component: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/join']}>{component}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockUseJoinQuestions.mockReturnValue({
    isPending: false,
    isError: false,
    data: [],
  } as unknown as ReturnType<typeof useJoinQuestions>);
  mockUseSubmitJoinRequest.mockReturnValue({
    isPending: false,
    isError: false,
    mutateAsync: vi.fn(),
  } as unknown as ReturnType<typeof useSubmitJoinRequest>);
});

describe('JoinScreen accessibility', () => {
  it('has no axe violations', async () => {
    const { container } = renderWith(<JoinScreen />);
    const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(results).toHaveNoViolations();
  }, 15000);

  it('submit action is discoverable by role', () => {
    renderWith(<JoinScreen />);
    expect(screen.getByRole('button', { name: /submit request/i })).toBeInTheDocument();
  });

  it('form fields follow logical source order for tab traversal', () => {
    renderWith(<JoinScreen />);
    const displayName = screen.getByLabelText(/display name/i);
    const phone = screen.getByLabelText(/phone number/i);
    const submit = screen.getByRole('button', { name: /submit request/i });

    const all = Array.from(document.querySelectorAll('input, button, select, textarea'));
    const nameIdx = all.indexOf(displayName);
    const phoneIdx = all.indexOf(phone);
    const submitIdx = all.indexOf(submit);

    expect(nameIdx).toBeGreaterThanOrEqual(0);
    expect(nameIdx).toBeLessThan(phoneIdx);
    expect(phoneIdx).toBeLessThan(submitIdx);
  });
});
