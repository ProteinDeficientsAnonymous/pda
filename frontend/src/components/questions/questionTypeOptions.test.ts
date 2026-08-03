import { describe, expect, it } from 'vitest';

import type { SurveyQuestionType } from '@/api/surveys';

import {
  JOIN_QUESTION_TYPE_OPTIONS,
  QUESTION_TYPE_OPTIONS,
  RSVP_QUESTION_TYPE_OPTIONS,
  questionOptionsError,
  questionTypeWantsOptions,
} from './questionTypeOptions';

const FULL_TYPES: SurveyQuestionType[] = [
  'text',
  'textarea',
  'select',
  'multiselect',
  'dropdown',
  'number',
  'yes_no',
  'rating',
  'datetime_poll',
];

describe('question type options', () => {
  it('should expose metadata for every survey/catalog type', () => {
    expect(QUESTION_TYPE_OPTIONS.map((o) => o.value).sort()).toEqual([...FULL_TYPES].sort());
  });

  it('should expose the canonical join subset when rendering authoring controls', () => {
    expect(JOIN_QUESTION_TYPE_OPTIONS).toEqual([
      { value: 'text', label: 'short text', wantsOptions: false },
      { value: 'textarea', label: 'long text', wantsOptions: false },
      { value: 'dropdown', label: 'dropdown', wantsOptions: true },
    ]);
    expect(JOIN_QUESTION_TYPE_OPTIONS.map(({ value }) => questionTypeWantsOptions(value))).toEqual([
      false,
      false,
      true,
    ]);
  });

  it('should expose the RSVP subset projected from catalog metadata', () => {
    expect(RSVP_QUESTION_TYPE_OPTIONS.map((o) => o.value)).toEqual([
      'textarea',
      'dropdown',
      'multiselect',
    ]);
    expect(RSVP_QUESTION_TYPE_OPTIONS.every((o) => FULL_TYPES.includes(o.value))).toBe(true);
  });

  it('should keep join and RSVP option values inside the full catalog', () => {
    const full = new Set(FULL_TYPES);
    for (const option of [...JOIN_QUESTION_TYPE_OPTIONS, ...RSVP_QUESTION_TYPE_OPTIONS]) {
      expect(full.has(option.value)).toBe(true);
    }
  });

  it('should return generic validation copy when a question requires options', () => {
    expect(questionOptionsError(true, [])).toBe('add at least one option for this');
    expect(questionOptionsError(true, ['first'])).toBeNull();
    expect(questionOptionsError(false, [])).toBeNull();
  });
});
