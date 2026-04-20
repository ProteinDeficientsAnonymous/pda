// Venmo and Cash App both accept either a short handle or a full URL. We
// normalize to a URL on save (so stored values are always clickable) and
// prettify back to a handle on edit-form load when the URL matches the
// standard handle-path shape.

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
