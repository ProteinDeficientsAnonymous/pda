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

describe('QuestionField', () => {
  it('renders a single-line text field for text type', () => {
    render(<QuestionField question={base} value="" onChange={vi.fn()} />);
    expect(screen.getByRole('textbox', { name: 'notes required' }).tagName).toBe('INPUT');
  });

  it('renders a textarea for textarea type', () => {
    render(
      <QuestionField question={{ ...base, fieldType: 'textarea' }} value="" onChange={vi.fn()} />,
    );
    expect(screen.getByRole('textbox', { name: 'notes required' }).tagName).toBe('TEXTAREA');
  });

  it('marks required questions as required', () => {
    render(<QuestionField question={base} value="" onChange={vi.fn()} />);
    expect(screen.getByRole('textbox', { name: 'notes required' })).toBeInTheDocument();
  });

  it('marks optional questions as optional', () => {
    render(<QuestionField question={{ ...base, required: false }} value="" onChange={vi.fn()} />);
    expect(screen.getByRole('textbox', { name: 'notes optional' })).toBeInTheDocument();
  });
});
