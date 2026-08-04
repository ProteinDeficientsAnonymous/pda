export function toVenmoUrl(input: string | undefined): string {
  const trimmed = (input ?? '').trim();
  if (!trimmed) return '';
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  const handle = trimmed.replace(/^@/, '');
  return `https://venmo.com/u/${handle}`;
}

export function fromVenmoUrl(url: string): string {
  const match = /^https?:\/\/(?:www\.)?venmo\.com\/u\/([^/?#]+)\/?$/i.exec(url.trim());
  const handle = match?.[1];
  if (!handle) return url;
  return `@${handle}`;
}

export function toCashAppUrl(input: string | undefined): string {
  const trimmed = (input ?? '').trim();
  if (!trimmed) return '';
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  const handle = trimmed.replace(/^\$/, '');
  return `https://cash.app/$${handle}`;
}

export function fromCashAppUrl(url: string): string {
  const match = /^https?:\/\/(?:www\.)?cash\.app\/\$([^/?#]+)\/?$/i.exec(url.trim());
  const handle = match?.[1];
  if (!handle) return url;
  return `$${handle}`;
}

// Cash App's public web links support an amount path segment (cash.app/$tag/20)
// but have no documented/supported query param for a note — amount-only.
export function toCashAppPayUrl(cashappLink: string, opts: { price?: string }): string {
  const base = toCashAppUrl(cashappLink);
  if (!base) return base;
  const amount = parseCashAppAmount(opts.price);
  if (amount === null) return base;
  return `${base}/${amount}`;
}

function parseCashAppAmount(price: string | undefined): string | null {
  const trimmed = (price ?? '').trim().replace(/^\$/, '');
  if (!/^\d+(\.\d{1,2})?$/.test(trimmed)) return null;
  return trimmed;
}
