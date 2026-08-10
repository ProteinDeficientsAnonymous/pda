import { describe, expect, it } from 'vitest';

import { QuestionType } from './questionTypes';
import type { components } from './types.gen';

type OpenApiQuestionType = components['schemas']['QuestionType'];

describe('QuestionType', () => {
  it('should expose wire values as named members matching OpenAPI', () => {
    const expected: OpenApiQuestionType[] = [
      'text',
      'textarea',
      'radio',
      'select',
      'checkbox',
      'number',
      'boolean',
      'rating',
      'datetime_poll',
    ];

    expect(QuestionType.Text).toBe('text');
    expect(QuestionType.Textarea).toBe('textarea');
    expect(QuestionType.Radio).toBe('radio');
    expect(QuestionType.Select).toBe('select');
    expect(QuestionType.Checkbox).toBe('checkbox');
    expect(QuestionType.Number).toBe('number');
    expect(QuestionType.Boolean).toBe('boolean');
    expect(QuestionType.Rating).toBe('rating');
    expect(QuestionType.DatetimePoll).toBe('datetime_poll');
    expect(Object.values(QuestionType).sort()).toEqual([...expected].sort());
  });
});
