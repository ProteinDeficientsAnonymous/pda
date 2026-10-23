import { describe, expect, it } from 'vitest';

import { emptyEventFormValues, type EventFormValues } from '@/api/eventWrites';
import { EventType } from '@/models/event';

import { hasTemplatePlaceholders, walkTagIds, withOfficialTemplate } from './officialTemplate';

const templates = { officialWalk: 'walk copy', officialNonWalk: 'non-walk copy' };
const WALK_ID = 'tag-walk';

function values(overrides: Partial<EventFormValues> = {}): EventFormValues {
  return { ...emptyEventFormValues(), ...overrides };
}

describe('walkTagIds', () => {
  it('picks tags with the walk slug', () => {
    expect(
      walkTagIds([
        { id: WALK_ID, name: 'walk', slug: 'walk' },
        { id: 'tag-food', name: 'food', slug: 'food' },
      ]),
    ).toEqual([WALK_ID]);
  });

  it('handles tags not loaded yet', () => {
    expect(walkTagIds(undefined)).toEqual([]);
  });
});

describe('withOfficialTemplate', () => {
  it('fills the non-walk template for an official event with an empty description', () => {
    const out = withOfficialTemplate(
      values({ eventType: EventType.Official }),
      [WALK_ID],
      templates,
    );
    expect(out.description).toBe('non-walk copy');
  });

  it('fills the walk template when the walk tag is selected', () => {
    const out = withOfficialTemplate(
      values({ eventType: EventType.Official, tagIds: [WALK_ID] }),
      [WALK_ID],
      templates,
    );
    expect(out.description).toBe('walk copy');
  });

  it('swaps templates while the description is untouched', () => {
    const out = withOfficialTemplate(
      values({ eventType: EventType.Official, tagIds: [WALK_ID], description: 'non-walk copy' }),
      [WALK_ID],
      templates,
    );
    expect(out.description).toBe('walk copy');
  });

  it('never overwrites a description the planner edited', () => {
    const v = values({ eventType: EventType.Official, description: 'my own words' });
    expect(withOfficialTemplate(v, [WALK_ID], templates)).toBe(v);
  });

  it('clears an untouched template when the event stops being official', () => {
    const out = withOfficialTemplate(
      values({ eventType: EventType.Community, description: 'walk copy' }),
      [WALK_ID],
      templates,
    );
    expect(out.description).toBe('');
  });

  it('leaves non-official events with an empty description alone', () => {
    const v = values({ eventType: EventType.Club });
    expect(withOfficialTemplate(v, [WALK_ID], templates)).toBe(v);
  });

  it('does nothing until templates load', () => {
    const v = values({ eventType: EventType.Official });
    expect(withOfficialTemplate(v, [WALK_ID], undefined)).toBe(v);
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
