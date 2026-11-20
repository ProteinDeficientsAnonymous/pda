import { describe, expect, it } from 'vitest';

import { centsToDollars, dollarsToCents, formatCents } from './orderPrice';

describe('dollarsToCents', () => {
  it.each([
    ['12', 1200],
    ['$12.5', 1250],
    [' $ 0.99 ', 99],
    ['0', 0],
    ['10000', 1_000_000],
  ])('reads %j as %d cents', (text, cents) => {
    expect(dollarsToCents(text)).toBe(cents);
  });

  it.each(['', 'free', '-1', '1.234', '10000.01', '1,000'])('rejects %j', (text) => {
    expect(dollarsToCents(text)).toBeNull();
  });
});

describe('centsToDollars', () => {
  it('drops zero cents and keeps two places otherwise', () => {
    expect(centsToDollars(1200)).toBe('12');
    expect(centsToDollars(1250)).toBe('12.50');
    expect(formatCents(99)).toBe('$0.99');
  });
});
