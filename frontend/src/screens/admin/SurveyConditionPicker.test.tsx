import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ShowIfOperator, type SurveyQuestion } from '@/api/surveys';
import { eligibleSourceQuestions } from '@/components/questions/questionVisibility';

import { SurveyConditionPicker } from './SurveyConditionPicker';

function question(overrides: Partial<SurveyQuestion> & Pick<SurveyQuestion, 'id'>): SurveyQuestion {
  return {
    label: overrides.id,
    fieldType: 'radio',
    options: ['vegan', 'veg'],
    required: false,
    displayOrder: 0,
    showIf: null,
    ...overrides,
  };
}

const diet = question({ id: 'diet', label: 'diet', displayOrder: 0 });
const notes = question({ id: 'notes', label: 'notes', fieldType: 'text', displayOrder: 1 });

describe('eligibleSourceQuestions', () => {
  it('keeps only choice and boolean questions', () => {
    const yesNo = question({ id: 'member', fieldType: 'boolean', options: [], displayOrder: 2 });
    expect(eligibleSourceQuestions([diet, notes, yesNo]).map((q) => q.id)).toEqual([
      'diet',
      'member',
    ]);
  });

  it('excludes questions at or below the one being edited', () => {
    const later = question({ id: 'later', displayOrder: 5 });
    const editing = question({ id: 'editing', displayOrder: 3 });
    expect(eligibleSourceQuestions([diet, later, editing], editing).map((q) => q.id)).toEqual([
      'diet',
    ]);
  });
});

describe('SurveyConditionPicker', () => {
  it('explains when nothing is eligible', () => {
    render(<SurveyConditionPicker questions={[notes]} value={null} onChange={vi.fn()} />);
    expect(screen.getByText(/add a choice or yes\/no question above/)).toBeInTheDocument();
  });

  it('explains a stored condition whose source is no longer eligible', () => {
    const stale = {
      questionId: 'gone',
      operator: ShowIfOperator.Equals,
      value: 'vegan',
    };
    render(<SurveyConditionPicker questions={[diet]} value={stale} onChange={vi.fn()} />);
    expect(screen.getByRole('checkbox', { name: 'only show when' })).toBeChecked();
    expect(screen.getByText(/can no longer be a source/)).toBeInTheDocument();
    expect(screen.queryByRole('combobox', { name: 'question' })).not.toBeInTheDocument();
  });

  it('creates a default condition when toggled on', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SurveyConditionPicker questions={[diet]} value={null} onChange={onChange} />);
    await user.click(screen.getByRole('checkbox', { name: 'only show when' }));
    expect(onChange).toHaveBeenCalledWith({
      questionId: 'diet',
      operator: ShowIfOperator.Equals,
      value: 'vegan',
    });
  });

  it('clears the condition when toggled off', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <SurveyConditionPicker
        questions={[diet]}
        value={{ questionId: 'diet', operator: ShowIfOperator.Equals, value: 'vegan' }}
        onChange={onChange}
      />,
    );
    await user.click(screen.getByRole('checkbox', { name: 'only show when' }));
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it('lists the source question options as answers', () => {
    render(
      <SurveyConditionPicker
        questions={[diet]}
        value={{ questionId: 'diet', operator: ShowIfOperator.Equals, value: 'vegan' }}
        onChange={vi.fn()}
      />,
    );
    const answer = screen.getByRole('combobox', { name: 'answer' });
    expect([...answer.querySelectorAll('option')].map((o) => o.value)).toEqual(['vegan', 'veg']);
  });

  it('offers "includes" only for checkbox sources', () => {
    const interests = question({
      id: 'interests',
      fieldType: 'checkbox',
      options: ['food', 'art'],
      displayOrder: 0,
    });
    const { rerender } = render(
      <SurveyConditionPicker
        questions={[diet]}
        value={{ questionId: 'diet', operator: ShowIfOperator.Equals, value: 'vegan' }}
        onChange={vi.fn()}
      />,
    );
    expect(screen.queryByRole('option', { name: 'includes' })).not.toBeInTheDocument();

    rerender(
      <SurveyConditionPicker
        questions={[interests]}
        value={{ questionId: 'interests', operator: ShowIfOperator.Equals, value: 'food' }}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole('option', { name: 'includes' })).toBeInTheDocument();
  });
});
