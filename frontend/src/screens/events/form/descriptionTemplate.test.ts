import { describe, expect, it } from 'vitest';

import { emptyEventFormValues, type EventFormValues } from '@/api/eventWrites';
import { EventType } from '@/models/event';

import { hasTemplatePlaceholders, withDescriptionTemplate } from './descriptionTemplate';

const templates = {
  officialWalk: 'walk copy',
  officialNonWalk: 'non-walk copy',
  club: 'club copy',
};

function values(overrides: Partial<EventFormValues> = {}): EventFormValues {
  return { ...emptyEventFormValues(), ...overrides };
}

describe('withDescriptionTemplate', () => {
  it('fills the walk template by default for a new official event', () => {
    const out = withDescriptionTemplate(values({ eventType: EventType.Official }), templates);
    expect(out.description).toBe('walk copy');
  });

  it('fills the non-walk template when the format is restaurant', () => {
    const out = withDescriptionTemplate(
      values({ eventType: EventType.Official, eventFormat: 'restaurant' }),
      templates,
    );
    expect(out.description).toBe('non-walk copy');
  });

  it('swaps to the non-walk template when the format switches to restaurant on an untouched description', () => {
    const out = withDescriptionTemplate(
      values({
        eventType: EventType.Official,
        eventFormat: 'restaurant',
        description: 'walk copy',
      }),
      templates,
    );
    expect(out.description).toBe('non-walk copy');
  });

  it('swaps back to the walk template when the format switches back to walk', () => {
    const out = withDescriptionTemplate(
      values({ eventType: EventType.Official, eventFormat: 'walk', description: 'non-walk copy' }),
      templates,
    );
    expect(out.description).toBe('walk copy');
  });

  it('fills the non-walk template when the format is unset', () => {
    const out = withDescriptionTemplate(
      values({ eventType: EventType.Official, eventFormat: null }),
      templates,
    );
    expect(out.description).toBe('non-walk copy');
  });

  it('never overwrites a description the planner edited', () => {
    const v = values({
      eventType: EventType.Official,
      eventFormat: 'restaurant',
      description: 'my own words',
    });
    expect(withDescriptionTemplate(v, templates)).toBe(v);
  });

  it('clears an untouched template when the event stops being official', () => {
    const out = withDescriptionTemplate(
      values({ eventType: EventType.Community, description: 'walk copy' }),
      templates,
    );
    expect(out.description).toBe('');
  });

  it('fills the club template for a new club event', () => {
    const out = withDescriptionTemplate(values({ eventType: EventType.Club }), templates);
    expect(out.description).toBe('club copy');
  });

  it('swaps an untouched club template for the official one', () => {
    const out = withDescriptionTemplate(
      values({ eventType: EventType.Official, eventFormat: 'walk', description: 'club copy' }),
      templates,
    );
    expect(out.description).toBe('walk copy');
  });

  it('clears an untouched club template when the event becomes community', () => {
    const out = withDescriptionTemplate(
      values({ eventType: EventType.Community, description: 'club copy' }),
      templates,
    );
    expect(out.description).toBe('');
  });

  it('leaves community events with an empty description alone', () => {
    const v = values({ eventType: EventType.Community });
    expect(withDescriptionTemplate(v, templates)).toBe(v);
  });

  it('does nothing until templates load', () => {
    const v = values({ eventType: EventType.Official });
    expect(withDescriptionTemplate(v, undefined)).toBe(v);
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
