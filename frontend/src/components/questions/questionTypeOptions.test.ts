import { describe, expect, it } from 'vitest';

import type { QuestionType } from '@/api/questionTypes';
import type { SurveyQuestionType } from '@/api/surveys';
import type { components } from '@/api/types.gen';

import {
  QUESTION_TYPE_OPTIONS,
  questionOptionsError,
  questionTypeWantsOptions,
} from './questionTypeOptions';

type AssertExtends<_A extends B, B> = true;
type _SurveyIsCatalog = AssertExtends<SurveyQuestionType, QuestionType>;
type _CatalogMatchesOpenApi = AssertExtends<
  QuestionType,
  components['schemas']['SurveyQuestionType']
>;

const FULL_TYPES: QuestionType[] = [
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
  it('should expose metadata for every catalog type', () => {
    expect(QUESTION_TYPE_OPTIONS.map((o) => o.value).sort()).toEqual([...FULL_TYPES].sort());
  });

  it('should look up wantsOptions from the catalog', () => {
    expect(questionTypeWantsOptions('text')).toBe(false);
    expect(questionTypeWantsOptions('dropdown')).toBe(true);
  });

  it('should return generic validation copy when a question requires options', () => {
    expect(questionOptionsError(true, [])).toBe('add at least one option');
    expect(questionOptionsError(true, ['first'])).toBeNull();
    expect(questionOptionsError(false, [])).toBeNull();
  });
});
