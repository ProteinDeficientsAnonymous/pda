import type { Event } from '@/models/event';

export function eventRequiresPaymentConfirmation(event: Event): boolean {
  const hasPrice = event.price.trim().length > 0;
  const hasPaymentMethod = [event.venmoLink, event.cashappLink, event.zelleInfo].some(
    (value) => value.trim().length > 0,
  );
  return hasPrice && hasPaymentMethod;
}

// A bare number gets a "$" prefix unless the user already typed one.
// Anything else (e.g. "sliding scale") passes through as-written.
export function formatPrice(price: string): string {
  const trimmed = price.trim();
  if (!trimmed) return trimmed;
  if (/^\$/.test(trimmed)) return trimmed;
  if (/^\d/.test(trimmed)) return `$${trimmed}`;
  return trimmed;
}
