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
    expect(screen.getByLabelText('notes (optional)')).toBeInTheDocument();
  });

  it('renders select one as a select and reports changes', () => {
    const onChange = vi.fn();
    render(
      <RsvpQuestionFields questions={questions} answers={{}} onChange={onChange} errors={{}} />,
    );
    const select = screen.getByRole('combobox', { name: 'transport' });
    fireEvent.change(select, { target: { value: 'car' } });
    expect(onChange).toHaveBeenCalledWith('q-one', 'car');
  });

  it('toggles checkbox options as csv', () => {
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
    expect(onChange).toHaveBeenCalledWith('q-multi', 'setup,cleanup');
    fireEvent.click(screen.getByRole('checkbox', { name: 'setup' }));
    expect(onChange).toHaveBeenCalledWith('q-multi', '');
  });

  it('should render questions in array order and keep answers keyed by id', () => {
    const { container } = render(
      <RsvpQuestionFields
        questions={[questions[1]!, questions[0]!]}
        answers={{ 'q-text': 'hello', 'q-one': 'bus' }}
        onChange={vi.fn()}
        errors={{}}
      />,
    );

    const labels = [...container.querySelectorAll('label')].map((label) => label.textContent);
    expect(labels[0]).toBe('transport');
    expect(labels[1]).toBe('notes (optional)');
    expect(screen.getByRole('combobox', { name: 'transport' })).toHaveValue('bus');
    expect(screen.getByLabelText('notes (optional)')).toHaveValue('hello');
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
    expect(screen.getByText('required')).toBeInTheDocument();
  });
});
