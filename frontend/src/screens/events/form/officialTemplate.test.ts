import { describe, expect, it } from 'vitest';

import { emptyEventFormValues, type EventFormValues } from '@/api/eventWrites';
import { EventType } from '@/models/event';

import { hasTemplatePlaceholders, withOfficialTemplate } from './officialTemplate';

const templates = { officialWalk: 'walk copy', officialNonWalk: 'non-walk copy' };

function values(overrides: Partial<EventFormValues> = {}): EventFormValues {
  return { ...emptyEventFormValues(), ...overrides };
}

describe('withOfficialTemplate', () => {
  it('fills the walk template by default for a new official event', () => {
    const out = withOfficialTemplate(values({ eventType: EventType.Official }), templates);
    expect(out.description).toBe('walk copy');
  });

  it('fills the non-walk template when walk is off', () => {
    const out = withOfficialTemplate(
      values({ eventType: EventType.Official, isWalk: false }),
      templates,
    );
    expect(out.description).toBe('non-walk copy');
  });

  it('swaps to the non-walk template when walk is turned off on an untouched description', () => {
    const out = withOfficialTemplate(
      values({ eventType: EventType.Official, isWalk: false, description: 'walk copy' }),
      templates,
    );
    expect(out.description).toBe('non-walk copy');
  });

  it('swaps back to the walk template when walk is turned on again', () => {
    const out = withOfficialTemplate(
      values({ eventType: EventType.Official, isWalk: true, description: 'non-walk copy' }),
      templates,
    );
    expect(out.description).toBe('walk copy');
  });

  it('never overwrites a description the planner edited', () => {
    const v = values({ eventType: EventType.Official, isWalk: false, description: 'my own words' });
    expect(withOfficialTemplate(v, templates)).toBe(v);
  });

  it('clears an untouched template when the event stops being official', () => {
    const out = withOfficialTemplate(
      values({ eventType: EventType.Community, description: 'walk copy' }),
      templates,
    );
    expect(out.description).toBe('');
  });

  it('leaves non-official events with an empty description alone', () => {
    const v = values({ eventType: EventType.Club });
    expect(withOfficialTemplate(v, templates)).toBe(v);
  });

  it('does nothing until templates load', () => {
    const v = values({ eventType: EventType.Official });
    expect(withOfficialTemplate(v, undefined)).toBe(v);
  });
});

describe('hasTemplatePlaceholders', () => {
  it('spots uppercase bracketed placeholders', () => {
    expect(hasTemplatePlaceholders('meet at [MEETING SPOT] at 6')).toBe(true);
    expect(hasTemplatePlaceholders('about [X] miles')).toBe(true);
  });

  it('ignores filled-in text and lowercase brackets', () => {
    expect(hasTemplatePlaceholders('meet at the park gate at 6')).toBe(false);
    expect(hasTemplatePlaceholders('bring snacks [optional]')).toBe(false);
  });
});
