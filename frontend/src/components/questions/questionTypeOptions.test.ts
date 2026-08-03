import { describe, expect, it } from 'vitest';

import { JOIN_QUESTION_TYPE_OPTIONS, questionTypeWantsOptions } from './questionTypeOptions';

describe('join question type options', () => {
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
});
