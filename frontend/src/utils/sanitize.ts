// Client-side defense-in-depth sanitizer for rendered Delta / ProseMirror HTML.
// Kept equivalent to the backend `sanitize_content_html` on tags, URL handling,
// and the text-align allowlist.

import DOMPurify from 'dompurify';

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

const ALLOWED_TEXT_ALIGN = new Set(['left', 'center', 'right']);
// Anchored to a declaration boundary so `-webkit-text-align` doesn't match while
// a real text-align among `;`-separated siblings does (mirrors the backend).
const TEXT_ALIGN_RE = /(?:^|;)\s*text-align:\s*([a-z]+)/i;

// Fold the browser transforms `new URL` alone misses: strip tab/LF/CR anywhere,
// and fold backslashes to "/" only before any ?/# (browsers don't fold them in
// the query, so "?x=a\b" survives). Mirrors the backend `_normalize_url`.
function normalizeUrl(value: string): string {
  const stripped = value.replace(/[\t\n\r]/g, '');
  const cut = stripped.search(/[?#]/);
  if (cut === -1) return stripped.replace(/\\/g, '/');
  return stripped.slice(0, cut).replace(/\\/g, '/') + stripped.slice(cut);
}

const SANITIZE_BASE_ORIGIN = 'https://pda.invalid';
const URL_SCHEME_RE = /^[a-z][a-z0-9+.-]*:/i;

// True if a scheme-less URL resolves off-origin (protocol-relative). Parsing
// against a fixed base ends the obfuscation arms race that substring checks lose.
function isProtocolRelative(normalized: string): boolean {
  if (URL_SCHEME_RE.test(normalized)) return false;
  try {
    return new URL(normalized, `${SANITIZE_BASE_ORIGIN}/`).origin !== SANITIZE_BASE_ORIGIN;
  } catch {
    return false;
  }
}

// Registered once at module load; sanitizeHtml is the only DOMPurify consumer.
DOMPurify.addHook('uponSanitizeAttribute', (_node, data) => {
  if (data.attrName === 'href' || data.attrName === 'src') {
    const normalized = normalizeUrl(data.attrValue);
    // Image src is http/https/relative only (DOMPurify would keep data:/mailto:).
    const badImgScheme =
      data.attrName === 'src' && URL_SCHEME_RE.test(normalized) && !/^https?:/i.test(normalized);
    if (isProtocolRelative(normalized) || badImgScheme) {
      data.attrValue = '';
      data.keepAttr = false;
    } else {
      data.attrValue = normalized;
    }
    return;
  }

  if (data.attrName !== 'style') return;
  const match = TEXT_ALIGN_RE.exec(data.attrValue);
  const value = match?.[1]?.toLowerCase();
  if (value && ALLOWED_TEXT_ALIGN.has(value)) {
    data.attrValue = `text-align: ${value}`;
    return;
  }
  data.attrValue = '';
  data.keepAttr = false;
});

// Force a safe rel on new-tab anchors — DOMPurify allowlists rel but won't add it.
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
