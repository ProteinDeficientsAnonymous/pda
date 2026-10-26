import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { QuestionType } from '@/api/questionTypes';
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
  it('renders five stars in a row and reports the picked one', () => {
    const onChange = vi.fn();
    render(
      <QuestionField
        question={{ ...base, fieldType: QuestionType.Stars }}
        value="2"
        onChange={onChange}
      />,
    );
    expect(screen.getAllByRole('radio')).toHaveLength(5);
    expect(screen.getByRole('radio', { name: '2 stars' })).toBeChecked();
    fireEvent.click(screen.getByRole('radio', { name: '4 stars' }));
    expect(onChange).toHaveBeenCalledWith('4');
  });

  it('renders a 1–5 scale with its end labels and reports the picked point', () => {
    const onChange = vi.fn();
    render(
      <QuestionField
        question={{ ...base, fieldType: QuestionType.Scale, options: ['bad', 'great'] }}
        value="3"
        onChange={onChange}
      />,
    );
    expect(screen.getByRole('radio', { name: '3' })).toBeChecked();
    expect(screen.getByText('bad')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('radio', { name: '5 — great' }));
    expect(onChange).toHaveBeenCalledWith('5');
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
