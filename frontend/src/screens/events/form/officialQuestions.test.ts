import { describe, expect, it } from 'vitest';

import type { OfficialRsvpQuestion } from '@/api/officialEventDefaults';
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

const official: OfficialRsvpQuestion[] = [
  { label: 'paid?', fieldType: QuestionType.Select, options: ['Yes'], required: true },
  { label: 'photos ok?', fieldType: QuestionType.Select, options: ['Yes', 'No'], required: true },
];

function withOfficial(questions: RsvpQuestionDraft[], isOfficial: boolean) {
  return withOfficialQuestions(questions, isOfficial, official);
}

describe('withOfficialQuestions', () => {
  it('adds the official questions after existing ones', () => {
    const out = withOfficial([custom], true);
    expect(out).toHaveLength(3);
    expect(out[0]).toBe(custom);
    const added = out.slice(1);
    expect(added.map(({ id: _id, ...q }) => q)).toEqual(official);
    expect(new Set(added.map((q) => q.id)).size).toBe(2);
  });

  it('does not duplicate questions already present', () => {
    const once = withOfficial([], true);
    expect(withOfficial(once, true)).toBe(once);
  });

  it('removes untouched official questions when the event stops being official', () => {
    const out = withOfficial(withOfficial([custom], true), false);
    expect(out).toEqual([custom]);
  });

  it('keeps official questions the planner edited', () => {
    const [first, ...rest] = withOfficial([], true);
    const edited = { ...first!, required: false };
    const out = withOfficial([edited, ...rest], false);
    expect(out).toEqual([edited]);
  });

  it('leaves non-official questions alone', () => {
    const qs = [custom];
    expect(withOfficial(qs, false)).toBe(qs);
  });
});
