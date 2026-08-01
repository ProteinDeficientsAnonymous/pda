import { describe, expect, it } from 'vitest';

import {
  isAnswerFilled,
  missingRequiredQuestionIds,
  parseOptionsText,
  type RsvpQuestionDraft,
  wantsOptions,
} from './rsvpQuestions';

const q = (
  overrides: Partial<RsvpQuestionDraft> & Pick<RsvpQuestionDraft, 'id'>,
): RsvpQuestionDraft => ({
  label: 'q',
  fieldType: 'textarea',
  options: [],
  required: false,
  ...overrides,
});

describe('wantsOptions', () => {
  it('is true only for choice types', () => {
    expect(wantsOptions('textarea')).toBe(false);
    expect(wantsOptions('dropdown')).toBe(true);
    expect(wantsOptions('multiselect')).toBe(true);
  });
});

describe('parseOptionsText', () => {
  it('splits trimmed non-empty lines', () => {
    expect(parseOptionsText('  a\n\nb  \n')).toEqual(['a', 'b']);
  });
});

describe('isAnswerFilled', () => {
  it('treats empty or whitespace as unfilled', () => {
    expect(isAnswerFilled(undefined)).toBe(false);
    expect(isAnswerFilled('')).toBe(false);
    expect(isAnswerFilled('  ')).toBe(false);
    expect(isAnswerFilled('yes')).toBe(true);
  });
});

describe('missingRequiredQuestionIds', () => {
  it('returns ids of required questions without answers', () => {
    const questions = [
      q({ id: 'a', required: true }),
      q({ id: 'b', required: false }),
      q({ id: 'c', required: true, fieldType: 'multiselect' }),
    ];
    expect(missingRequiredQuestionIds(questions, { a: 'ok', c: '' })).toEqual(['c']);
    expect(missingRequiredQuestionIds(questions, { a: 'ok', c: 'x' })).toEqual([]);
  });
});
