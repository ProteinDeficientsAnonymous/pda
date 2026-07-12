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

// Mirrors the backend's `_normalize_url`: apply the two browser transforms that
// a string check (or even URL parsing) misses, so the stored value matches what
// every consumer resolves. Tab/LF/CR are removed from anywhere (browsers do this
// before parsing); backslashes fold to "/" but ONLY in the authority/path
// (before any ?/#), since browsers don't fold them in the query/fragment — so a
// legit backslash in a query string ("?x=a\b") isn't corrupted.
function normalizeUrl(value: string): string {
  const stripped = value.replace(/[\t\n\r]/g, '');
  const cut = stripped.search(/[?#]/);
  if (cut === -1) return stripped.replace(/\\/g, '/');
  return stripped.slice(0, cut).replace(/\\/g, '/') + stripped.slice(cut);
}

// True if a (normalised) href/src resolves to an off-site authority with no
// explicit scheme — i.e. a protocol-relative URL ("//evil.com", "/\evil.com",
// "/\t/evil.com", ...) a browser sends off-site. We parse with `new URL` rather
// than substring-match: resolving against a fixed base, a protocol-relative URL
// lands on a foreign origin while a genuine relative path ("/media/...") stays
// same-origin, and absolute scheme-bearing URLs are excluded up front (DOMPurify
// already vetted their scheme). Parsing ends the obfuscation arms race.
const SANITIZE_BASE_ORIGIN = 'https://pda.invalid';
const URL_SCHEME_RE = /^[a-z][a-z0-9+.-]*:/i;

function isProtocolRelative(normalized: string): boolean {
  if (URL_SCHEME_RE.test(normalized)) return false;
  try {
    return new URL(normalized, `${SANITIZE_BASE_ORIGIN}/`).origin !== SANITIZE_BASE_ORIGIN;
  } catch {
    return false; // unparseable — leave it for DOMPurify's own URI policy
  }
}

// The hooks are static (no per-call state) and DOMPurify is a module singleton,
// so register them once at module load rather than re-checking on every call.
// sanitizeHtml is the only DOMPurify consumer in the app; if that ever changes,
// scope these to an isolated DOMPurify instance instead of the global one.

DOMPurify.addHook('uponSanitizeAttribute', (_node, data) => {
  // Reject protocol-relative URLs on href/src. DOMPurify keeps "//evil.com" as a
  // valid relative URL, but it resolves off-site — a remote-load / phishing
  // vector. Normalise browser obfuscations, then parse to decide. Genuine
  // relative paths ("/media/...") stay.
  if (data.attrName === 'href' || data.attrName === 'src') {
    const normalized = normalizeUrl(data.attrValue);
    // Image src is http/https/relative only, matching the backend's scheme guard
    // (rejects data:, mailto:, etc. that DOMPurify would otherwise keep on <img>).
    const badImgScheme =
      data.attrName === 'src' &&
      URL_SCHEME_RE.test(normalized) &&
      !/^https?:/i.test(normalized);
    if (isProtocolRelative(normalized) || badImgScheme) {
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
