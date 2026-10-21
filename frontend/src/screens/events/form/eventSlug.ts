export const EVENT_SLUG_MAX_LENGTH = 80;

// Mirrors the backend's _EVENT_SLUG_RE.
const EVENT_SLUG_PATTERN = /^[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?$/;
const UUID_PATTERN = /^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$/;

export function toEventSlugInput(raw: string): string {
  return raw
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9_-]/g, '');
}

export function eventSlugError(slug: string): string | undefined {
  if (!slug) return 'required';
  if (slug.length > EVENT_SLUG_MAX_LENGTH) {
    return `under ${String(EVENT_SLUG_MAX_LENGTH)} chars`;
  }
  if (!EVENT_SLUG_PATTERN.test(slug) || UUID_PATTERN.test(slug)) {
    return 'use lowercase letters, numbers, and dashes — start and end with a letter or number';
  }
  return undefined;
}
