import { describe, it, expect } from 'vitest';
import { cn } from './cn';

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('a', 'b')).toBe('a b');
  });

  it('resolves tailwind conflicts', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4');
  });

  it('handles conditionals', () => {
    const disabled = false as boolean;
    expect(cn('a', disabled && 'b', 'c')).toBe('a c');
  });
});
