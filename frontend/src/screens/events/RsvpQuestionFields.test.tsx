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
    fieldType: 'dropdown',
    options: ['car', 'bus'],
    required: true,
  },
  {
    id: 'q-multi',
    label: 'help with',
    fieldType: 'multiselect',
    options: ['setup', 'cleanup'],
    required: false,
  },
];

describe('RsvpQuestionFields', () => {
  it('marks optional free response in the label', () => {
    render(
      <RsvpQuestionFields questions={questions} answers={{}} onChange={vi.fn()} errors={{}} />,
    );
    expect(screen.getByLabelText('notes (optional)')).toBeInTheDocument();
  });

  it('renders select one as a dropdown and reports changes', () => {
    const onChange = vi.fn();
    render(
      <RsvpQuestionFields questions={questions} answers={{}} onChange={onChange} errors={{}} />,
    );
    const select = screen.getByRole('combobox', { name: 'transport' });
    fireEvent.change(select, { target: { value: 'car' } });
    expect(onChange).toHaveBeenCalledWith('q-one', 'car');
  });

  it('toggles multiselect options', () => {
    const onChange = vi.fn();
    render(
      <RsvpQuestionFields
        questions={questions}
        answers={{ 'q-multi': ['setup'] }}
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
    expect(screen.getByRole('alert')).toHaveTextContent('required');
  });
});
