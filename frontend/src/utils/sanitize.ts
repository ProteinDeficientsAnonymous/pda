// DOMPurify wrapper with defaults tuned for PDA's rendered Quill Delta /
// ProseMirror HTML. The backend produces this HTML via delta_to_html /
// prosemirror_to_html; we sanitize again on the client as defense-in-depth
// (the backend isn't the only path — future edits, pasted content, etc. could
// flow through).

import DOMPurify from 'dompurify';

// Allowlist mirrors exactly what the renderers emit (delta_to_html /
// prosemirror_to_html): headings h1–h3, lists, inline emphasis (strong/em/u/s),
// inline code, links, images, blockquote, hr. Anything else (script, iframe,
// on* handlers) is stripped. Kept in sync with the backend _ALLOWED_TAGS.
const ALLOWED_TAGS = [
  'a',
  'em',
  'strong',
  'u',
  's',
  'p',
  'br',
  'h1',
  'h2',
  'h3',
  'ul',
  'ol',
  'li',
  'blockquote',
  'code',
  'img',
  'hr',
];

// `style` is intentionally allowed but tightly constrained — the renderers emit
// `style="text-align: left|center|right"` for block alignment (there is no
// class-based equivalent). The uponSanitizeAttribute hook below strips every
// declaration except text-align, so arbitrary CSS injection is neutralized.
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

// Matches the renderers' alignment vocabulary (left/center/right) and the
// backend's _ALLOWED_TEXT_ALIGN. Anything else is dropped.
const ALLOWED_TEXT_ALIGN = new Set(['left', 'center', 'right']);

// The hooks are static (no per-call state) and DOMPurify is a module singleton,
// so register them once at module load rather than re-checking on every call.
// sanitizeHtml is the only DOMPurify consumer in the app; if that ever changes,
// scope these to an isolated DOMPurify instance instead of the global one.

DOMPurify.addHook('uponSanitizeAttribute', (_node, data) => {
  // Reject protocol-relative URLs on href/src. DOMPurify keeps "//evil.com" as a
  // valid relative URL, but it resolves to https://evil.com — an off-site /
  // remote-load vector. Normalise browser-equivalent obfuscations first (leading
  // whitespace/controls are ignored by the URL parser; backslashes resolve as
  // forward slashes), matching the backend's _normalize_url, so "/\evil.com" and
  // "https:/\evil.com" can't slip past a naive `//` check. Genuine relative
  // paths ("/media/...") stay.
  if (data.attrName === 'href' || data.attrName === 'src') {
    // eslint-disable-next-line no-control-regex
    const normalized = data.attrValue.replace(/^[\x00-\x20\x7f]+/, '').replace(/\\/g, '/');
    if (normalized.startsWith('//')) {
      data.attrValue = '';
      data.keepAttr = false;
    } else {
      data.attrValue = normalized;
    }
    return;
  }

  // Constrain `style` to a single safe declaration: text-align with a known
  // value. Anything else (positioning, url(), expression(), etc.) is dropped.
  if (data.attrName !== 'style') return;
  const match = /text-align:\s*([a-z]+)/i.exec(data.attrValue);
  const value = match?.[1]?.toLowerCase();
  if (value && ALLOWED_TEXT_ALIGN.has(value)) {
    data.attrValue = `text-align: ${value}`;
    return;
  }
  data.attrValue = '';
  data.keepAttr = false;
});

// DOMPurify's ADD_ATTR only allowlists target/rel — it does not *force* a
// safe rel. Any anchor opening a new tab must get rel="noopener noreferrer"
// to block reverse-tabnabbing, regardless of what (if any) rel was supplied.
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName !== 'A') return;
  if (node.getAttribute('target') === '_blank') {
    node.setAttribute('rel', 'noopener noreferrer');
  }
});

export function sanitizeHtml(raw: string): string {
  return DOMPurify.sanitize(raw, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
    ADD_ATTR: ['target', 'rel'],
  });
}
