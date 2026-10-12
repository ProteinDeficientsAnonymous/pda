import { describe, expect, it } from 'vitest';

import { QuestionType } from '@/api/questionTypes';
import { RsvpServerStatus } from '@/models/event';
import { makeEvent, makeGuest } from '@/test/fixtures';

import {
  guestShowsQuestionnaire,
  hasSavedQuestionnaireResponses,
  isAnswerFilled,
  missingRequiredQuestionIds,
  type RsvpQuestionDraft,
  rsvpQuestionsApplyToStatus,
  shouldShowRsvpQuestions,
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

describe('shouldShowRsvpQuestions', () => {
  const base = {
    questionCount: 1,
    mode: 'edit' as const,
    changedFromInitial: false,
  };

  it('should hide questions when an existing maybe stays maybe', () => {
    expect(shouldShowRsvpQuestions({ ...base, status: RsvpServerStatus.Maybe })).toBe(false);
  });

  it('should show questions when status changes to maybe', () => {
    expect(
      shouldShowRsvpQuestions({
        ...base,
        status: RsvpServerStatus.Maybe,
        changedFromInitial: true,
      }),
    ).toBe(true);
  });

  it('should show questions when creating a maybe rsvp', () => {
    expect(
      shouldShowRsvpQuestions({ ...base, status: RsvpServerStatus.Maybe, mode: 'create' }),
    ).toBe(true);
  });

  it('should show questions after leaving maybe and choosing it again', () => {
    expect(
      shouldShowRsvpQuestions({
        ...base,
        status: RsvpServerStatus.Maybe,
        changedFromInitial: true,
      }),
    ).toBe(true);
  });

  it('should keep showing questions for going', () => {
    expect(shouldShowRsvpQuestions({ ...base, status: RsvpServerStatus.Attending })).toBe(true);
  });
});

describe('hasSavedQuestionnaireResponses', () => {
  it('should ignore going guests who have no saved answers', () => {
    const event = makeEvent({
      guests: [makeGuest({ questionnaireResponses: {} })],
    });
    expect(hasSavedQuestionnaireResponses(event)).toBe(false);
  });

  it('should count a maybe guest who saved an answer', () => {
    const event = makeEvent({
      guests: [
        makeGuest({
          status: RsvpServerStatus.Maybe,
          questionnaireResponses: { q1: { label: 'q', answer: 'yes' } },
        }),
      ],
    });
    expect(hasSavedQuestionnaireResponses(event)).toBe(true);
  });
});

describe('guestShowsQuestionnaire', () => {
  it('should include maybe guests only when they have saved answers', () => {
    expect(guestShowsQuestionnaire(RsvpServerStatus.Maybe, 0)).toBe(false);
    expect(guestShowsQuestionnaire(RsvpServerStatus.Maybe, 1)).toBe(true);
    expect(guestShowsQuestionnaire(RsvpServerStatus.Attending, 0)).toBe(true);
    expect(guestShowsQuestionnaire(RsvpServerStatus.CantGo, 1)).toBe(false);
  });
});
