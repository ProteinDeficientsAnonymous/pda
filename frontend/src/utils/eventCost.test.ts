import { describe, expect, it } from 'vitest';

import { makePaidEvent } from '@/test/fixtures';

import { eventRequiresPaymentConfirmation, formatPrice, formatPriceWithNote } from './eventCost';

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

  it('requires confirmation with a price note and no amount', () => {
    const event = makePaidEvent({ price: '', priceNote: 'sliding scale $6–$8' });
    expect(eventRequiresPaymentConfirmation(event)).toBe(true);
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

describe('formatPriceWithNote', () => {
  it('joins the price and note', () => {
    expect(formatPriceWithNote({ price: '10', priceNote: 'deposit' })).toBe('$10 · deposit');
  });

  it('shows the note alone when there is no price', () => {
    expect(formatPriceWithNote({ price: '', priceNote: '$6–$8' })).toBe('$6–$8');
  });

  it('shows the price alone when there is no note', () => {
    expect(formatPriceWithNote({ price: '10', priceNote: ' ' })).toBe('$10');
  });
});
