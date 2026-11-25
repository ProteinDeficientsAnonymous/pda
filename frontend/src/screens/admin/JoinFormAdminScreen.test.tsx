import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import type { JoinQuestion } from '@/api/join';

import JoinFormAdminScreen from './JoinFormAdminScreen';

const questions: JoinQuestion[] = [
  {
    id: 'q1',
    label: 'why join?',
    fieldType: 'text',
    options: [],
    required: true,
    displayOrder: 0,
    managed: false,
  },
  {
    id: 'q2',
    label: 'which clubs?',
    fieldType: 'checkbox',
    options: [],
    required: false,
    displayOrder: 1,
    managed: true,
  },
];

vi.mock('@/api/join', () => ({
  DEFAULT_JOIN_QUESTION_TYPE: 'text',
  useJoinQuestions: () => ({ data: questions, isPending: false, isError: false }),
  useReorderJoinQuestions: () => ({ mutate: vi.fn() }),
  useDeleteJoinQuestion: () => ({ mutate: vi.fn() }),
  useCreateJoinQuestion: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateJoinQuestion: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

describe('JoinFormAdminScreen', () => {
  it('shows a managed question read-only with a link to clubs', () => {
    render(
      <MemoryRouter>
        <JoinFormAdminScreen />
      </MemoryRouter>,
    );
    expect(screen.getByRole('button', { name: 'edit why join?' })).toBeInTheDocument();
    expect(screen.getByText('which clubs?')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'edit which clubs?' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'delete which clubs?' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'managed in clubs' })).toHaveAttribute(
      'href',
      '/admin/clubs',
    );
  });
});
