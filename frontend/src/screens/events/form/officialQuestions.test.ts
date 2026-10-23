import { describe, expect, it } from 'vitest';

import { QuestionType } from '@/api/questionTypes';

import type { RsvpQuestionDraft } from '../rsvpQuestions';
import { withOfficialQuestions } from './officialQuestions';

const custom: RsvpQuestionDraft = {
  id: 'q-custom',
  label: 'any allergies?',
  fieldType: QuestionType.Textarea,
  options: [],
  required: false,
};

describe('withOfficialQuestions', () => {
  it('adds the four required official questions after existing ones', () => {
    const out = withOfficialQuestions([custom], true);
    expect(out).toHaveLength(5);
    expect(out[0]).toBe(custom);
    const added = out.slice(1);
    expect(added.every((q) => q.required && q.fieldType === QuestionType.Select)).toBe(true);
    expect(added.slice(0, 3).every((q) => q.options.length === 1 && q.options[0] === 'Yes')).toBe(
      true,
    );
    expect(added[3]?.options).toEqual([
      'Yes, I consent to being on the IG',
      "No, I'd like to opt out",
    ]);
    expect(new Set(added.map((q) => q.id)).size).toBe(4);
  });

  it('does not duplicate questions already present', () => {
    const once = withOfficialQuestions([], true);
    expect(withOfficialQuestions(once, true)).toBe(once);
  });

  it('removes untouched official questions when the event stops being official', () => {
    const out = withOfficialQuestions(withOfficialQuestions([custom], true), false);
    expect(out).toEqual([custom]);
  });

  it('keeps official questions the planner edited', () => {
    const [first, ...rest] = withOfficialQuestions([], true);
    const edited = { ...first!, required: false };
    const out = withOfficialQuestions([edited, ...rest], false);
    expect(out).toEqual([edited]);
  });

  it('leaves non-official questions alone', () => {
    const qs = [custom];
    expect(withOfficialQuestions(qs, false)).toBe(qs);
  });
});
