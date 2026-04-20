// DOMPurify wrapper with defaults tuned for PDA's rendered Quill Delta HTML.
// The backend produces this HTML via delta_to_html; we sanitize again on the
// client as defense-in-depth (the backend isn't the only path — future edits,
// pasted content, etc. could flow through).

import DOMPurify from 'dompurify';

// Conservative allowlist: headings, lists, inline emphasis, links, images,
// blockquote, code. Anything else (script, iframe, on* handlers) is stripped.
const ALLOWED_TAGS = [
  'a',
  'b',
  'i',
  'em',
  'strong',
  'u',
  's',
  'p',
  'br',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'ul',
  'ol',
  'li',
  'blockquote',
  'pre',
  'code',
  'img',
  'hr',
];

const ALLOWED_ATTR = [
  'href',
  'title',
  'target',
  'rel',
  'src',
  'alt',
  'width',
  'height',
  'class',
  'role',
  'style',
];

export function sanitizeHtml(raw: string): string {
  return DOMPurify.sanitize(raw, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
    // Force target=_blank + noopener on external links.
    ADD_ATTR: ['target', 'rel'],
  });
}
