import type { Event } from '@/models/event';
import { ensureHttps } from '@/utils/url';

// Strip scheme + optional www. and trailing slash for display. `href` should
// still get the full URL (via ensureHttps).
function prettyUrl(url: string): string {
  return url
    .replace(/^https?:\/\//i, '')
    .replace(/^www\./i, '')
    .replace(/\/$/, '');
}

export function buildEventLinks(event: Event): { label: string; url: string }[] {
  const links: { label: string; url: string }[] = [];
  if (event.whatsappLink) {
    links.push({ label: 'whatsapp group', url: ensureHttps(event.whatsappLink) });
  }
  if (event.partifulLink) links.push({ label: 'partiful', url: ensureHttps(event.partifulLink) });
  if (event.otherLink) {
    links.push({ label: prettyUrl(event.otherLink), url: ensureHttps(event.otherLink) });
  }
  return links;
}
