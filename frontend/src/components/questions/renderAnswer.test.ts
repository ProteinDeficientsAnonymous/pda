import { format } from 'date-fns';
import { describe, expect, it } from 'vitest';

import { renderAnswer } from './renderAnswer';

describe('renderAnswer', () => {
  it('shows a dash when there is no answer', () => {
    expect(renderAnswer(undefined)).toBe('—');
    expect(renderAnswer(null)).toBe('—');
  });

  it('unwraps string answers', () => {
    expect(renderAnswer({ label: 'q', answer: 'yes' })).toBe('yes');
    expect(renderAnswer('plain')).toBe('plain');
  });

  it('puts each list answer on its own line so commas inside options stay readable', () => {
    expect(renderAnswer({ label: 'q', answer: ['a, b', 'c'] })).toBe('a, b\nc');
  });

  it('joins object answers one pair per line', () => {
    expect(renderAnswer({ label: 'q', answer: { a: '1', b: '2' } })).toBe('a: 1\nb: 2');
  });

  it('formats datetime poll keys as readable local times', () => {
    const iso = '2026-11-07T16:00:00.000Z';
    const expected = format(new Date(iso), 'MMM d, yyyy h:mm a').toLowerCase();
    expect(renderAnswer({ label: 'q', answer: { [iso]: 'yes' } })).toBe(`${expected}: yes`);
  });

  it('stringifies other answer shapes', () => {
    expect(renderAnswer({ label: 'q', answer: 4 })).toBe('4');
  });
});
