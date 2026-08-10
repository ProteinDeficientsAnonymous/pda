import { fireEvent, render, screen } from '@testing-library/react';
import type { SyntheticEvent } from 'react';
import { describe, expect, it, vi } from 'vitest';

import type { RsvpQuestionDraft } from '../rsvpQuestions';
import { EventFormQuestions } from './EventFormQuestions';

const sample: RsvpQuestionDraft = {
  id: 'q1',
  label: 'bring anything?',
  fieldType: 'textarea',
  options: [],
  required: true,
};

describe('EventFormQuestions', () => {
  it('prompts to enable rsvp when rsvp is off', () => {
    render(<EventFormQuestions rsvpEnabled={false} questions={[]} onQuestionsChange={vi.fn()} />);
    expect(
      screen.getByText(/enable rsvp to ask guests questions when they respond/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /add question/i })).not.toBeInTheDocument();
  });

  it('shows empty state and add button when rsvp is on', () => {
    render(<EventFormQuestions rsvpEnabled questions={[]} onQuestionsChange={vi.fn()} />);
    expect(screen.getByText('no questions yet')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add question/i })).toBeInTheDocument();
  });

  it('lists questions with type and required marker', () => {
    render(<EventFormQuestions rsvpEnabled questions={[sample]} onQuestionsChange={vi.fn()} />);
    expect(screen.getByText('bring anything?')).toBeInTheDocument();
    expect(screen.getByText(/short answer/)).toBeInTheDocument();
    expect(screen.getByText(/required/)).toBeInTheDocument();
  });

  it('removes a question when delete is clicked', () => {
    const onQuestionsChange = vi.fn();
    render(
      <EventFormQuestions rsvpEnabled questions={[sample]} onQuestionsChange={onQuestionsChange} />,
    );
    fireEvent.click(screen.getByRole('button', { name: /delete/i }));
    expect(onQuestionsChange).toHaveBeenCalledWith([]);
  });

  it('opens add dialog from add question', () => {
    render(<EventFormQuestions rsvpEnabled questions={[]} onQuestionsChange={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /add question/i }));
    expect(screen.getByRole('dialog', { name: /add question/i })).toBeInTheDocument();
  });

  it('saving a question does not submit a wrapping event form', () => {
    const onParentSubmit = vi.fn((e: SyntheticEvent) => {
      e.preventDefault();
    });
    const onQuestionsChange = vi.fn();
    render(
      <form onSubmit={onParentSubmit}>
        <EventFormQuestions rsvpEnabled questions={[]} onQuestionsChange={onQuestionsChange} />
      </form>,
    );
    fireEvent.click(screen.getByRole('button', { name: /add question/i }));
    fireEvent.change(screen.getByLabelText('question'), { target: { value: 'dietary needs' } });
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }));
    expect(onQuestionsChange).toHaveBeenCalledWith([
      expect.objectContaining({ label: 'dietary needs' }),
    ]);
    expect(onParentSubmit).not.toHaveBeenCalled();
  });
});
