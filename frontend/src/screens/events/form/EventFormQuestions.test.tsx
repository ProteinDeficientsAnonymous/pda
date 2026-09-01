import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

const secondQuestion: RsvpQuestionDraft = {
  id: 'q2',
  label: 'dietary needs?',
  fieldType: 'textarea',
  options: [],
  required: false,
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

  it('should explain questions only show for going or waitlisted guests', () => {
    render(<EventFormQuestions rsvpEnabled questions={[]} onQuestionsChange={vi.fn()} />);
    expect(screen.getByText('shown when guests rsvp as going or waitlisted')).toBeInTheDocument();
    expect(screen.queryByText(/going or maybe/i)).not.toBeInTheDocument();
  });

  it('lists questions with type and required marker', () => {
    render(<EventFormQuestions rsvpEnabled questions={[sample]} onQuestionsChange={vi.fn()} />);
    expect(screen.getByText('bring anything?')).toBeInTheDocument();
    expect(screen.getByText(/short answer/)).toBeInTheDocument();
    expect(screen.getByText(/required/)).toBeInTheDocument();
  });

  it('reorders loaded questions with the keyboard drag control', async () => {
    const onQuestionsChange = vi.fn();
    const rect = (top: number): DOMRect =>
      ({
        bottom: top + 50,
        height: 50,
        left: 0,
        right: 300,
        top,
        width: 300,
        x: 0,
        y: top,
        toJSON: () => ({}),
      }) as DOMRect;
    const rectSpy = vi
      .spyOn(HTMLElement.prototype, 'getBoundingClientRect')
      .mockImplementation(function (this: HTMLElement) {
        return rect(this.textContent?.includes(secondQuestion.label) ? 60 : 0);
      });
    render(
      <EventFormQuestions
        rsvpEnabled
        questions={[sample, secondQuestion]}
        onQuestionsChange={onQuestionsChange}
      />,
    );

    const firstDragControl = screen.getAllByRole('button', { name: 'drag to reorder' })[0]!;
    firstDragControl.focus();
    await userEvent.keyboard('[Space][ArrowDown][Space]');

    expect(onQuestionsChange).toHaveBeenCalledWith([secondQuestion, sample]);
    rectSpy.mockRestore();
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
