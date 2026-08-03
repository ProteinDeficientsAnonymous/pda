import { describe, expect, it } from 'vitest';

import type { JoinQuestionType } from '@/api/join';
import type { QuestionType } from '@/api/questionTypes';
import type { components } from '@/api/types.gen';
import { questionTypeWantsOptions } from '@/components/questions/questionTypeOptions';

import { JOIN_QUESTION_TYPE_OPTIONS } from './joinQuestionTypeOptions';

type AssertExtends<_A extends B, B> = true;
type _JoinSubsetOfCatalog = AssertExtends<JoinQuestionType, QuestionType>;
type _JoinMatchesOpenApi = AssertExtends<
  JoinQuestionType,
  components['schemas']['JoinFormQuestionType']
>;

describe('join question type options', () => {
  it('should expose the join subset projected from catalog metadata', () => {
    expect(JOIN_QUESTION_TYPE_OPTIONS).toEqual([
      { value: 'text', label: 'short text', wantsOptions: false },
      { value: 'textarea', label: 'long text', wantsOptions: false },
      { value: 'select', label: 'select', wantsOptions: true },
    ]);
    expect(JOIN_QUESTION_TYPE_OPTIONS.map(({ value }) => questionTypeWantsOptions(value))).toEqual([
      false,
      false,
      true,
    ]);
  });

  it('should match backend join subset wire values', () => {
    expect(JOIN_QUESTION_TYPE_OPTIONS.map((o) => o.value)).toEqual(['text', 'textarea', 'select']);
  });
});
