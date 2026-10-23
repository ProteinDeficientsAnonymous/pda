import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { QuestionType } from '@/api/questionTypes';

import type { QuestionAuthorValues } from './QuestionAuthorDialog';
import { QuestionCardEditor } from './QuestionCardEditor';
import { QUESTION_TYPE_OPTIONS } from './questionTypeOptions';

const TYPE_OPTIONS = QUESTION_TYPE_OPTIONS.map((t) => ({ value: t.value, label: t.label }));

function renderCard(value: Partial<QuestionAuthorValues> = {}) {
  const onSave = vi.fn().mockResolvedValue(undefined);
  render(
    <QuestionCardEditor
      id="q1"
      value={{
        label: 'favorite food',
        fieldType: QuestionType.Text,
        options: [],
        required: false,
        ...value,
      }}
      typeOptions={TYPE_OPTIONS}
      onSave={onSave}
    />,
  );
  return { onSave };
}

describe('QuestionCardEditor', () => {
  it('does not save when a field blurs without changes', () => {
    const { onSave } = renderCard();
    fireEvent.blur(screen.getByLabelText('question'));
    expect(onSave).not.toHaveBeenCalled();
  });

  it('trims the label before saving', async () => {
    const { onSave } = renderCard();
    const input = screen.getByLabelText('question');
    fireEvent.change(input, { target: { value: '  tofu or tempeh?  ' } });
    fireEvent.blur(input);
    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ label: 'tofu or tempeh?' }));
    });
    expect(await screen.findByText('saved')).toBeInTheDocument();
  });

  it('refuses to save a blank label', () => {
    const { onSave } = renderCard();
    const input = screen.getByLabelText('question');
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.blur(input);
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('question text required');
  });

  it('seeds a first option when switching to a choice type', async () => {
    const { onSave } = renderCard();
    fireEvent.change(screen.getByLabelText('question type'), {
      target: { value: QuestionType.Radio },
    });
    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith(
        expect.objectContaining({ fieldType: QuestionType.Radio, options: ['option 1'] }),
      );
    });
    expect(screen.getByDisplayValue('option 1')).toBeInTheDocument();
  });

  it('saves immediately when an option is removed', async () => {
    const { onSave } = renderCard({ fieldType: QuestionType.Radio, options: ['a', 'b'] });
    fireEvent.click(screen.getByRole('button', { name: 'remove option 1' }));
    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ options: ['b'] }));
    });
  });

  it('saves the required toggle immediately', async () => {
    const { onSave } = renderCard();
    fireEvent.click(screen.getByRole('switch', { name: 'required' }));
    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ required: true }));
    });
  });

  it('allows a rating with no star labels', async () => {
    const { onSave } = renderCard();
    fireEvent.change(screen.getByLabelText('question type'), {
      target: { value: QuestionType.Rating },
    });
    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith(
        expect.objectContaining({ fieldType: QuestionType.Rating, options: [] }),
      );
    });
  });

  it('shows the server error when a save fails', async () => {
    const onSave = vi.fn().mockRejectedValue(new Error('boom'));
    render(
      <QuestionCardEditor
        id="q1"
        value={{ label: 'x', fieldType: QuestionType.Text, options: [], required: false }}
        typeOptions={TYPE_OPTIONS}
        onSave={onSave}
      />,
    );
    fireEvent.click(screen.getByRole('switch', { name: 'required' }));
    expect(await screen.findByRole('alert')).toHaveTextContent("couldn't save — try again");
  });
});
