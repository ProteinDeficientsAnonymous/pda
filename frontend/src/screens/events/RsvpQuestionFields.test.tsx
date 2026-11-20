import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { RsvpQuestionFields } from './RsvpQuestionFields';
import type { RsvpQuestionDraft } from './rsvpQuestions';

const questions: RsvpQuestionDraft[] = [
  {
    id: 'q-text',
    label: 'notes',
    fieldType: 'textarea',
    options: [],
    required: false,
  },
  {
    id: 'q-one',
    label: 'transport',
    fieldType: 'select',
    options: ['car', 'bus'],
    required: true,
  },
  {
    id: 'q-multi',
    label: 'help with',
    fieldType: 'checkbox',
    options: ['setup', 'cleanup'],
    required: false,
  },
];

describe('RsvpQuestionFields', () => {
  it('marks optional free response in the label', () => {
    render(
      <RsvpQuestionFields questions={questions} answers={{}} onChange={vi.fn()} errors={{}} />,
    );
    expect(screen.getByLabelText('notes')).toBeInTheDocument();
  });

  it('renders select one as a select and reports changes', () => {
    const onChange = vi.fn();
    render(
      <RsvpQuestionFields questions={questions} answers={{}} onChange={onChange} errors={{}} />,
    );
    const select = screen.getByRole('combobox', { name: 'transport · required' });
    fireEvent.change(select, { target: { value: 'car' } });
    expect(onChange).toHaveBeenCalledWith('q-one', 'car');
  });

  it('toggles checkbox options as a list', () => {
    const onChange = vi.fn();
    render(
      <RsvpQuestionFields
        questions={questions}
        answers={{ 'q-multi': 'setup' }}
        onChange={onChange}
        errors={{}}
      />,
    );
    fireEvent.click(screen.getByRole('checkbox', { name: 'cleanup' }));
    expect(onChange).toHaveBeenCalledWith('q-multi', ['setup', 'cleanup']);
    fireEvent.click(screen.getByRole('checkbox', { name: 'setup' }));
    expect(onChange).toHaveBeenCalledWith('q-multi', []);
  });

  it('shows per-question errors', () => {
    render(
      <RsvpQuestionFields
        questions={questions}
        answers={{}}
        onChange={vi.fn()}
        errors={{ 'q-one': 'required' }}
      />,
    );
    expect(screen.getByText('required', { selector: 'p' })).toBeInTheDocument();
  });

  it('lists option prices and the live total for priced questions', () => {
    const priced: RsvpQuestionDraft[] = [
      { ...questions[1]!, optionPrices: [500, 250] },
      { ...questions[2]!, optionPrices: [1000, 1250] },
    ];
    render(
      <RsvpQuestionFields
        questions={priced}
        answers={{ 'q-one': 'car', 'q-multi': ['setup', 'cleanup'] }}
        onChange={vi.fn()}
        errors={{}}
      />,
    );

    expect(screen.getByText('car $5 · bus $2.50')).toBeInTheDocument();
    expect(screen.getByText('your total: $27.50')).toBeInTheDocument();
  });

  it('shows no total without priced questions', () => {
    render(
      <RsvpQuestionFields questions={questions} answers={{}} onChange={vi.fn()} errors={{}} />,
    );
    expect(screen.queryByText(/your total/)).not.toBeInTheDocument();
  });
});
