import { describe, expect, it } from 'vitest';

import type { Survey, SurveyResponseAdmin } from '@/api/surveyAdmin';

import { removedQuestions } from './removedQuestions';

const survey = { questions: [{ id: 'q-kept' }] } as unknown as Survey;

function responseWith(answers: Record<string, unknown>): SurveyResponseAdmin {
  return { answers } as unknown as SurveyResponseAdmin;
}

describe('removedQuestions', () => {
  it('should list answer ids missing from the survey once, in first-seen order', () => {
    const responses = [
      responseWith({
        'q-kept': { label: 'kept', answer: 'a' },
        'q-b': { label: 'b?', answer: 'x' },
      }),
      responseWith({ 'q-a': { label: 'a?', answer: 'y' }, 'q-b': { label: 'b?', answer: 'z' } }),
    ];
    expect(removedQuestions(survey, responses)).toEqual([
      { id: 'q-b', label: 'b? (removed)' },
      { id: 'q-a', label: 'a? (removed)' },
    ]);
  });

  it('should fall back when the stored answer has no label', () => {
    expect(removedQuestions(survey, [responseWith({ 'q-x': 'bare' })])).toEqual([
      { id: 'q-x', label: 'removed question (removed)' },
    ]);
  });
});
