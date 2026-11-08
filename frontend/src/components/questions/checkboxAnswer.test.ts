import { describe, expect, it } from 'vitest';

import { checkboxValues } from './checkboxAnswer';

describe('checkboxValues', () => {
  it('keeps list items whole', () => {
    expect(checkboxValues([' a, b ', '', 'c'])).toEqual(['a, b', 'c']);
  });

  it('splits legacy comma strings', () => {
    expect(checkboxValues('a, b,,')).toEqual(['a', 'b']);
  });

  it('treats other shapes as nothing ticked', () => {
    expect(checkboxValues(undefined)).toEqual([]);
    expect(checkboxValues({ a: 'yes' })).toEqual([]);
  });
});
