import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

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

let shown: JoinQuestion[] = questions;

vi.mock('@/api/join', () => ({
  DEFAULT_JOIN_QUESTION_TYPE: 'text',
  useJoinQuestions: () => ({ data: shown, isPending: false, isError: false }),
  useReorderJoinQuestions: () => ({ mutate: vi.fn() }),
  useDeleteJoinQuestion: () => ({ mutate: vi.fn() }),
  useCreateJoinQuestion: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateJoinQuestion: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

function renderScreen() {
  render(
    <MemoryRouter>
      <JoinFormAdminScreen />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  shown = questions;
});

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

  it('shows the empty state when only managed questions exist', () => {
    shown = questions.filter((q) => q.managed);
    renderScreen();
    expect(screen.getByText('no custom questions yet')).toBeInTheDocument();
    expect(screen.getByText('which clubs?')).toBeInTheDocument();
  });

  it('omits the managed list when there are no managed questions', () => {
    shown = questions.filter((q) => !q.managed);
    renderScreen();
    expect(screen.getByRole('button', { name: 'edit why join?' })).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'managed questions' })).not.toBeInTheDocument();
  });
});
