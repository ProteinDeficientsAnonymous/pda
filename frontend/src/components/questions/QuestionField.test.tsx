import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { SurveyQuestion } from '@/api/surveys';

import { QuestionField } from './QuestionField';

const base: SurveyQuestion = {
  id: 'q1',
  label: 'notes',
  fieldType: 'text',
  options: [],
  required: true,
  displayOrder: 0,
};

describe('QuestionField rows', () => {
  it('renders a single-line text field when rows is 1', () => {
    render(<QuestionField question={{ ...base, rows: 1 }} value="" onChange={vi.fn()} />);
    expect(screen.getByRole('textbox', { name: 'notes' }).tagName).toBe('INPUT');
  });

  it('renders a textarea with the configured row count when rows > 1', () => {
    render(<QuestionField question={{ ...base, rows: 4 }} value="" onChange={vi.fn()} />);
    const el = screen.getByRole('textbox', { name: 'notes' });
    expect(el.tagName).toBe('TEXTAREA');
    expect(el).toHaveAttribute('rows', '4');
  });

  it('uses configured rows for textarea field type', () => {
    render(
      <QuestionField
        question={{ ...base, fieldType: 'textarea', rows: 8 }}
        value=""
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole('textbox', { name: 'notes' })).toHaveAttribute('rows', '8');
  });
});
