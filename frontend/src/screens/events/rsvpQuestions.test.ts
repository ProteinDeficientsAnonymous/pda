import { describe, expect, it } from 'vitest';

import { QuestionType } from '@/api/questionTypes';
import { RsvpServerStatus } from '@/models/event';

import {
  isAnswerFilled,
  missingRequiredQuestionIds,
  type RsvpQuestionDraft,
  rsvpQuestionsApplyToStatus,
  wantsOptions,
} from './rsvpQuestions';

const q = (
  overrides: Partial<RsvpQuestionDraft> & Pick<RsvpQuestionDraft, 'id'>,
): RsvpQuestionDraft => ({
  label: 'q',
  fieldType: QuestionType.Textarea,
  options: [],
  required: false,
  ...overrides,
});

describe('wantsOptions', () => {
  it('is true only for choice types', () => {
    expect(wantsOptions(QuestionType.Textarea)).toBe(false);
    expect(wantsOptions(QuestionType.Select)).toBe(true);
    expect(wantsOptions(QuestionType.Checkbox)).toBe(true);
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
      q({ id: 'c', required: true, fieldType: QuestionType.Checkbox }),
    ];
    expect(missingRequiredQuestionIds(questions, { a: 'ok', c: '' })).toEqual(['c']);
    expect(missingRequiredQuestionIds(questions, { a: 'ok', c: 'x' })).toEqual([]);
  });
});

describe('rsvpQuestionsApplyToStatus', () => {
  it('should apply only for going and waitlisted statuses', () => {
    expect(rsvpQuestionsApplyToStatus(RsvpServerStatus.Attending)).toBe(true);
    expect(rsvpQuestionsApplyToStatus(RsvpServerStatus.Waitlisted)).toBe(true);
    expect(rsvpQuestionsApplyToStatus(RsvpServerStatus.Maybe)).toBe(false);
    expect(rsvpQuestionsApplyToStatus(RsvpServerStatus.CantGo)).toBe(false);
  });
});
