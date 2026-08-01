import { describe, expect, it } from 'vitest';

import {
  isAnswerFilled,
  missingRequiredQuestionIds,
  parseOptionsText,
  questionsSectionSummary,
  type RsvpQuestionDraft,
  rsvpSectionSummary,
  wantsOptions,
} from './rsvpQuestions';

const q = (
  overrides: Partial<RsvpQuestionDraft> & Pick<RsvpQuestionDraft, 'id'>,
): RsvpQuestionDraft => ({
  label: 'q',
  fieldType: 'free_response',
  options: [],
  required: false,
  ...overrides,
});

describe('rsvpSectionSummary', () => {
  it('returns undefined when rsvp is off', () => {
    expect(rsvpSectionSummary(false)).toBeUndefined();
  });

  it('returns enabled when rsvp is on', () => {
    expect(rsvpSectionSummary(true)).toBe('enabled');
  });
});

describe('questionsSectionSummary', () => {
  it('returns undefined when empty', () => {
    expect(questionsSectionSummary(0)).toBeUndefined();
  });

  it('includes singular and plural question counts', () => {
    expect(questionsSectionSummary(1)).toBe('1 question');
    expect(questionsSectionSummary(2)).toBe('2 questions');
  });
});

describe('wantsOptions', () => {
  it('is true only for choice types', () => {
    expect(wantsOptions('free_response')).toBe(false);
    expect(wantsOptions('select_one')).toBe(true);
    expect(wantsOptions('select_multiple')).toBe(true);
  });
});

describe('parseOptionsText', () => {
  it('splits trimmed non-empty lines', () => {
    expect(parseOptionsText('  a\n\nb  \n')).toEqual(['a', 'b']);
  });
});

describe('isAnswerFilled', () => {
  it('treats empty string and empty array as unfilled', () => {
    expect(isAnswerFilled(undefined)).toBe(false);
    expect(isAnswerFilled('')).toBe(false);
    expect(isAnswerFilled('  ')).toBe(false);
    expect(isAnswerFilled([])).toBe(false);
    expect(isAnswerFilled('yes')).toBe(true);
    expect(isAnswerFilled(['a'])).toBe(true);
  });
});

describe('missingRequiredQuestionIds', () => {
  it('returns ids of required questions without answers', () => {
    const questions = [
      q({ id: 'a', required: true }),
      q({ id: 'b', required: false }),
      q({ id: 'c', required: true, fieldType: 'select_multiple' }),
    ];
    expect(missingRequiredQuestionIds(questions, { a: 'ok', c: [] })).toEqual(['c']);
    expect(missingRequiredQuestionIds(questions, { a: 'ok', c: ['x'] })).toEqual([]);
  });
});
