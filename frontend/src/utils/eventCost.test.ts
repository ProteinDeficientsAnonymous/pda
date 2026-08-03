import { describe, expect, it } from 'vitest';

import { makeEvent } from '@/test/fixtures';

import { eventRequiresPaymentConfirmation, formatPrice } from './eventCost';

function makePaidEvent(overrides: Parameters<typeof makeEvent>[0] = {}) {
  return makeEvent({
    price: '$10',
    venmoLink: 'https://venmo.com/u/host',
    cashappLink: '',
    zelleInfo: '',
    ...overrides,
  });
}

describe('eventRequiresPaymentConfirmation', () => {
  it('requires confirmation with a price and venmo', () => {
    expect(eventRequiresPaymentConfirmation(makePaidEvent())).toBe(true);
  });

  it('requires confirmation with a price and cashapp', () => {
    const event = makePaidEvent({ venmoLink: '', cashappLink: 'https://cash.app/$host' });
    expect(eventRequiresPaymentConfirmation(event)).toBe(true);
  });

  it('requires confirmation with a price and zelle', () => {
    const event = makePaidEvent({ venmoLink: '', zelleInfo: 'host@example.com' });
    expect(eventRequiresPaymentConfirmation(event)).toBe(true);
  });

  it('does not require confirmation with a price but no payment method', () => {
    expect(eventRequiresPaymentConfirmation(makePaidEvent({ venmoLink: '' }))).toBe(false);
  });

  it('does not require confirmation with a payment method but no price', () => {
    expect(eventRequiresPaymentConfirmation(makePaidEvent({ price: '' }))).toBe(false);
  });

  it('treats a whitespace-only price as no price', () => {
    expect(eventRequiresPaymentConfirmation(makePaidEvent({ price: '   ' }))).toBe(false);
  });

  it('treats a whitespace-only payment method as absent', () => {
    expect(eventRequiresPaymentConfirmation(makePaidEvent({ venmoLink: '  ' }))).toBe(false);
  });
});

describe('formatPrice', () => {
  it('prefixes a bare number with a dollar sign', () => {
    expect(formatPrice('10')).toBe('$10');
  });

  it('leaves an existing dollar sign alone', () => {
    expect(formatPrice('$10')).toBe('$10');
  });

  it('passes non-numeric text through as written', () => {
    expect(formatPrice('sliding scale')).toBe('sliding scale');
  });

  it('returns empty for blank input', () => {
    expect(formatPrice('   ')).toBe('');
  });
});
