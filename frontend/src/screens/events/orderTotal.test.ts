import { describe, expect, it } from 'vitest';

import { QuestionType } from '@/api/questionTypes';
import type { EventRsvpQuestion } from '@/models/event';

import { orderTotalCents, savedOrderTotalCents } from './orderTotal';

const meal: EventRsvpQuestion = {
  id: 'meal',
  label: 'meal',
  fieldType: QuestionType.Select,
  options: ['bowl', 'plate'],
  optionPrices: [1200, 1850],
  required: true,
};
const extras: EventRsvpQuestion = {
  id: 'extras',
  label: 'extras',
  fieldType: QuestionType.Checkbox,
  options: ['drink', 'dessert'],
  optionPrices: [300, 450],
  required: false,
};
const notes: EventRsvpQuestion = {
  id: 'notes',
  label: 'notes',
  fieldType: QuestionType.Textarea,
  options: [],
  required: false,
};

describe('orderTotalCents', () => {
  it('is null without a priced question', () => {
    expect(orderTotalCents([notes], { notes: 'hi' })).toBeNull();
  });

  it('adds the picked option and every ticked option', () => {
    expect(
      orderTotalCents([meal, extras, notes], { meal: 'plate', extras: ['drink', 'dessert'] }),
    ).toBe(2600);
  });

  it('is zero before anything is picked', () => {
    expect(orderTotalCents([meal], {})).toBe(0);
  });
});

describe('savedOrderTotalCents', () => {
  it('prefers the price saved with the answer', () => {
    expect(
      savedOrderTotalCents([meal], { meal: { label: 'meal', answer: 'plate', priceCents: 1500 } }),
    ).toBe(1500);
  });

  it("falls back to today's prices for answers saved before pricing", () => {
    expect(savedOrderTotalCents([meal], { meal: { label: 'meal', answer: 'bowl' } })).toBe(1200);
  });

  it('keeps a saved price after its question is deleted', () => {
    expect(
      savedOrderTotalCents([notes], { gone: { label: 'old', answer: 'x', priceCents: 900 } }),
    ).toBe(900);
  });

  it('is null when nothing is priced', () => {
    expect(savedOrderTotalCents([notes], { notes: { label: 'notes', answer: 'hi' } })).toBeNull();
  });
});
