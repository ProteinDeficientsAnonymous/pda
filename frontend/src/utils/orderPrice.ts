export const MAX_OPTION_PRICE_CENTS = 1_000_000;

/** return(null): not a dollar amount from $0 up to the option price cap. */
export function dollarsToCents(text: string): number | null {
  const cleaned = text.trim().replace(/^\$\s*/, '');
  if (!/^\d+(\.\d{1,2})?$/.test(cleaned)) return null;
  const cents = Math.round(Number(cleaned) * 100);
  return cents <= MAX_OPTION_PRICE_CENTS ? cents : null;
}

export function centsToDollars(cents: number): string {
  return cents % 100 === 0 ? String(cents / 100) : (cents / 100).toFixed(2);
}

export function formatCents(cents: number): string {
  return `$${centsToDollars(cents)}`;
}
