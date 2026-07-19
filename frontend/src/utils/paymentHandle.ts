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
