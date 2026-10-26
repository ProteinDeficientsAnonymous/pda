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

  it('stringifies other answer shapes', () => {
    expect(renderAnswer({ label: 'q', answer: 4 })).toBe('4');
  });
});
