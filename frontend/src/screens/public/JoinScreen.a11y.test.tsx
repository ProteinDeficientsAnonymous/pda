import { screen } from '@testing-library/react';
import type { ReactElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

import { useJoinQuestions, useSubmitJoinRequest } from '@/api/join';
import { renderWithProviders } from '@/test/render';

import JoinScreen from './JoinScreen';

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

const mockUseJoinQuestions = vi.mocked(useJoinQuestions);
const mockUseSubmitJoinRequest = vi.mocked(useSubmitJoinRequest);

function renderWith(component: ReactElement) {
  return renderWithProviders(component, { route: '/join' });
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

  it('has two labeled name inputs (first name, last name)', () => {
    renderWith(<JoinScreen />);
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/last name/i)).toBeInTheDocument();
  });

  it('form fields follow logical source order for tab traversal', () => {
    renderWith(<JoinScreen />);
    const firstName = screen.getByLabelText(/first name/i);
    const lastName = screen.getByLabelText(/last name/i);
    const phone = screen.getByLabelText(/phone number/i);
    const submit = screen.getByRole('button', { name: /submit request/i });

    const all = Array.from(document.querySelectorAll('input, button, select, textarea'));
    const firstNameIdx = all.indexOf(firstName);
    const lastNameIdx = all.indexOf(lastName);
    const phoneIdx = all.indexOf(phone);
    const submitIdx = all.indexOf(submit);

    expect(firstNameIdx).toBeGreaterThanOrEqual(0);
    expect(firstNameIdx).toBeLessThan(lastNameIdx);
    expect(lastNameIdx).toBeLessThan(phoneIdx);
    expect(phoneIdx).toBeLessThan(submitIdx);
  });
});
