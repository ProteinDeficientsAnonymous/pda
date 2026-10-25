import { describe, expect, it } from 'vitest';

import { mapQuestion } from './surveys';

describe('mapQuestion', () => {
  it('never marks a section header required', () => {
    const section = mapQuestion({
      id: 's1',
      label: 'about you',
      field_type: 'section',
      required: true,
      display_order: 0,
    });
    expect(section.required).toBe(false);
  });
});
