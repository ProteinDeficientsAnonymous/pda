import { describe, expect, it } from 'vitest';

import { type ShowIfCondition, ShowIfOperator, type SurveyQuestion } from '@/api/surveys';

import { visibleQuestionIds } from './questionVisibility';

function question(
  id: string,
  overrides: Partial<SurveyQuestion> & Pick<SurveyQuestion, 'fieldType' | 'displayOrder'>,
): SurveyQuestion {
  return {
    id,
    label: id,
    options: [],
    required: false,
    showIf: null,
    ...overrides,
  };
}

function equals(questionId: string, value: string): ShowIfCondition {
  return { questionId, operator: ShowIfOperator.Equals, value };
}

describe('visibleQuestionIds', () => {
  const diet = question('diet', {
    fieldType: 'radio',
    options: ['vegan', 'veg'],
    displayOrder: 0,
  });

  it('shows unconditional questions', () => {
    const plain = question('plain', { fieldType: 'text', displayOrder: 1 });
    expect(visibleQuestionIds([diet, plain], {})).toEqual(new Set(['diet', 'plain']));
  });

  it('shows a dependent only when its condition holds', () => {
    const why = question('why', {
      fieldType: 'text',
      displayOrder: 1,
      showIf: equals('diet', 'vegan'),
    });
    expect(visibleQuestionIds([diet, why], { diet: 'vegan' })).toEqual(new Set(['diet', 'why']));
    expect(visibleQuestionIds([diet, why], { diet: 'veg' })).toEqual(new Set(['diet']));
    expect(visibleQuestionIds([diet, why], {})).toEqual(new Set(['diet']));
  });

  it('supports not_equals', () => {
    const why = question('why', {
      fieldType: 'text',
      displayOrder: 1,
      showIf: { questionId: 'diet', operator: ShowIfOperator.NotEquals, value: 'vegan' },
    });
    expect(visibleQuestionIds([diet, why], { diet: 'veg' }).has('why')).toBe(true);
    expect(visibleQuestionIds([diet, why], { diet: 'vegan' }).has('why')).toBe(false);
  });

  it('matches one checked box with contains', () => {
    const interests = question('interests', {
      fieldType: 'checkbox',
      options: ['food', 'art'],
      displayOrder: 0,
    });
    const dish = question('dish', {
      fieldType: 'text',
      displayOrder: 1,
      showIf: { questionId: 'interests', operator: ShowIfOperator.Contains, value: 'food' },
    });
    expect(visibleQuestionIds([interests, dish], { interests: 'art,food' }).has('dish')).toBe(true);
    expect(visibleQuestionIds([interests, dish], { interests: 'art' }).has('dish')).toBe(false);
  });

  it('matches a list answer whose option contains a comma', () => {
    const clubs = 'club events (book club, movie club)';
    const interests = question('interests', {
      fieldType: 'checkbox',
      options: [clubs, 'potlucks'],
      displayOrder: 0,
    });
    const which = question('which', {
      fieldType: 'text',
      displayOrder: 1,
      showIf: { questionId: 'interests', operator: ShowIfOperator.Contains, value: clubs },
    });
    expect(visibleQuestionIds([interests, which], { interests: [clubs] }).has('which')).toBe(true);
    expect(visibleQuestionIds([interests, which], { interests: ['potlucks'] }).has('which')).toBe(
      false,
    );
  });

  it('treats not_equals on a checkbox as "not ticked"', () => {
    const interests = question('interests', {
      fieldType: 'checkbox',
      options: ['food', 'art'],
      displayOrder: 0,
    });
    const why = question('why', {
      fieldType: 'text',
      displayOrder: 1,
      showIf: { questionId: 'interests', operator: ShowIfOperator.NotEquals, value: 'food' },
    });
    expect(visibleQuestionIds([interests, why], { interests: 'food,art' }).has('why')).toBe(false);
    expect(visibleQuestionIds([interests, why], { interests: 'art' }).has('why')).toBe(true);
  });

  it('cascades hiding down a chain', () => {
    const member = question('member', {
      fieldType: 'boolean',
      displayOrder: 1,
      showIf: equals('diet', 'vegan'),
    });
    const since = question('since', {
      fieldType: 'text',
      displayOrder: 2,
      showIf: equals('member', 'yes'),
    });
    const answers = { diet: 'veg', member: 'yes' };
    expect(visibleQuestionIds([diet, member, since], answers)).toEqual(new Set(['diet']));
  });

  it('ignores a non-string answer on the source question', () => {
    const dependent = question('dependent', {
      fieldType: 'text',
      displayOrder: 1,
      showIf: equals('diet', 'vegan'),
    });
    expect(visibleQuestionIds([diet, dependent], { diet: { a: 'yes' } }).has('dependent')).toBe(
      false,
    );
  });
});
