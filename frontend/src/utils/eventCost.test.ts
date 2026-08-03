import { describe, expect, it } from 'vitest';

import type { Event } from '@/models/event';

import { eventRequiresPaymentConfirmation, formatPrice } from './eventCost';

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    price: '$10',
    venmoLink: 'https://venmo.com/u/host',
    cashappLink: '',
    zelleInfo: '',
    ...overrides,
  } as Event;
}

describe('eventRequiresPaymentConfirmation', () => {
  it('requires confirmation with a price and venmo', () => {
    expect(eventRequiresPaymentConfirmation(makeEvent())).toBe(true);
  });

  it('requires confirmation with a price and cashapp', () => {
    const event = makeEvent({ venmoLink: '', cashappLink: 'https://cash.app/$host' });
    expect(eventRequiresPaymentConfirmation(event)).toBe(true);
  });

  it('requires confirmation with a price and zelle', () => {
    const event = makeEvent({ venmoLink: '', zelleInfo: 'host@example.com' });
    expect(eventRequiresPaymentConfirmation(event)).toBe(true);
  });

  it('does not require confirmation with a price but no payment method', () => {
    expect(eventRequiresPaymentConfirmation(makeEvent({ venmoLink: '' }))).toBe(false);
  });

  it('does not require confirmation with a payment method but no price', () => {
    expect(eventRequiresPaymentConfirmation(makeEvent({ price: '' }))).toBe(false);
  });

  it('treats a whitespace-only price as no price', () => {
    expect(eventRequiresPaymentConfirmation(makeEvent({ price: '   ' }))).toBe(false);
  });

  it('treats a whitespace-only payment method as absent', () => {
    expect(eventRequiresPaymentConfirmation(makeEvent({ venmoLink: '  ' }))).toBe(false);
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
