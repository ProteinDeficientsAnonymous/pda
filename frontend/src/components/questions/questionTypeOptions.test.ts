import { describe, expect, it } from 'vitest';

import type { JoinQuestionType } from '@/api/join';
import { QuestionType } from '@/api/questionTypes';
import type { SurveyQuestionType } from '@/api/surveys';
import type { components } from '@/api/types.gen';

import {
  JOIN_QUESTION_TYPE_OPTIONS,
  QUESTION_TYPE_OPTIONS,
  questionOptionsError,
  questionTypeWantsOptions,
} from './questionTypeOptions';

type AssertExtends<_A extends B, B> = true;
type _SurveyIsCatalog = AssertExtends<SurveyQuestionType, QuestionType>;
type _CatalogMatchesOpenApi = AssertExtends<QuestionType, components['schemas']['QuestionType']>;
type _JoinSubsetOfCatalog = AssertExtends<JoinQuestionType, QuestionType>;
type _JoinMatchesOpenApi = AssertExtends<
  JoinQuestionType,
  components['schemas']['JoinFormQuestionType']
>;

const FULL_TYPES: QuestionType[] = Object.values(QuestionType);

describe('question type options', () => {
  it('should expose metadata for every catalog type from QuestionType members', () => {
    expect(QUESTION_TYPE_OPTIONS.map((o) => o.value).sort()).toEqual([...FULL_TYPES].sort());
    expect(QUESTION_TYPE_OPTIONS.find((o) => o.value === QuestionType.Text)).toEqual({
      value: QuestionType.Text,
      label: 'short text',
      wantsOptions: false,
    });
    expect(QUESTION_TYPE_OPTIONS.find((o) => o.value === QuestionType.Select)).toEqual({
      value: QuestionType.Select,
      label: 'select',
      wantsOptions: true,
    });
  });

  it('should look up wantsOptions from the catalog', () => {
    expect(questionTypeWantsOptions(QuestionType.Text)).toBe(false);
    expect(questionTypeWantsOptions(QuestionType.Select)).toBe(true);
  });

  it('should return generic validation copy when a question requires options', () => {
    expect(questionOptionsError(true, [])).toBe('add at least one option');
    expect(questionOptionsError(true, ['first'])).toBeNull();
    expect(questionOptionsError(false, [])).toBeNull();
  });

  it('should expose the join subset projected from catalog metadata', () => {
    expect(JOIN_QUESTION_TYPE_OPTIONS).toEqual([
      { value: QuestionType.Text, label: 'short text', wantsOptions: false },
      { value: QuestionType.Textarea, label: 'long text', wantsOptions: false },
      { value: QuestionType.Select, label: 'select', wantsOptions: true },
    ]);
    expect(JOIN_QUESTION_TYPE_OPTIONS.map(({ value }) => questionTypeWantsOptions(value))).toEqual([
      false,
      false,
      true,
    ]);
  });
});
