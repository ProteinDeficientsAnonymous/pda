import { describe, expect, it } from 'vitest';

import { toCashAppPayUrl } from './paymentHandle';

describe('toCashAppPayUrl', () => {
  it('appends a clean numeric price as the amount segment', () => {
    expect(toCashAppPayUrl('$handle', { price: '20' })).toBe('https://cash.app/$handle/20');
  });

  it('strips a leading dollar sign from the price', () => {
    expect(toCashAppPayUrl('$handle', { price: '$20.50' })).toBe('https://cash.app/$handle/20.50');
  });

  it('falls back to the plain profile link for a non-numeric price', () => {
    expect(toCashAppPayUrl('$handle', { price: 'sliding scale' })).toBe('https://cash.app/$handle');
  });

  it('falls back to the plain profile link for an empty price', () => {
    expect(toCashAppPayUrl('$handle', { price: '' })).toBe('https://cash.app/$handle');
  });
});
