import { fireEvent, render, screen } from '@testing-library/react';
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
  showIf: null,
};

describe('QuestionField', () => {
  it('renders bare stars when a rating has no labels', () => {
    render(
      <QuestionField question={{ ...base, fieldType: 'rating' }} value="" onChange={vi.fn()} />,
    );
    expect(screen.getByRole('radio', { name: '3 stars' })).toHaveTextContent('★');
    expect(screen.getByRole('radiogroup')).not.toHaveClass('flex-col');
  });

  it('keeps labeled stars in one row with each label under its star', () => {
    render(
      <QuestionField
        question={{ ...base, fieldType: 'rating', options: ['meh', '', '', '', 'loved it'] }}
        value=""
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole('radiogroup')).not.toHaveClass('flex-col');
    expect(screen.getByRole('radio', { name: 'loved it' })).toHaveTextContent('loved it');
    expect(screen.getByRole('radio', { name: '2 stars' })).toHaveTextContent(/^★$/);
  });

  it('lets a datetime poll answer no for a time', () => {
    const onChange = vi.fn();
    render(
      <QuestionField
        question={{ ...base, fieldType: 'datetime_poll', options: ['2026-11-07T16:00:00Z'] }}
        value={{}}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByRole('radio', { name: 'no' }));
    expect(onChange).toHaveBeenCalledWith({ '2026-11-07T16:00:00Z': 'no' });
  });

  it('renders a single-line text field for text type', () => {
    render(<QuestionField question={base} value="" onChange={vi.fn()} />);
    expect(screen.getByRole('textbox', { name: 'notes · required' }).tagName).toBe('INPUT');
  });

  it('renders a textarea for textarea type', () => {
    render(
      <QuestionField question={{ ...base, fieldType: 'textarea' }} value="" onChange={vi.fn()} />,
    );
    expect(screen.getByRole('textbox', { name: 'notes · required' }).tagName).toBe('TEXTAREA');
  });

  it('marks required questions as required', () => {
    render(<QuestionField question={base} value="" onChange={vi.fn()} />);
    expect(screen.getByRole('textbox', { name: 'notes · required' })).toBeInTheDocument();
  });

  it('leaves optional questions unmarked', () => {
    render(<QuestionField question={{ ...base, required: false }} value="" onChange={vi.fn()} />);
    expect(screen.getByRole('textbox', { name: 'notes' })).toBeInTheDocument();
    expect(screen.queryByText(/optional/)).not.toBeInTheDocument();
  });

  it('renders a section as a heading with its description and no input', () => {
    render(
      <QuestionField
        question={{ ...base, fieldType: 'section', label: 'about you', description: 'optional' }}
        value={undefined}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole('heading', { name: 'about you' })).toBeInTheDocument();
    expect(screen.getByText('optional')).toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });
});
