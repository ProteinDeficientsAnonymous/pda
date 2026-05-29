// DOMPurify wrapper with defaults tuned for PDA's rendered Quill Delta /
// ProseMirror HTML. The backend produces this HTML via delta_to_html /
// prosemirror_to_html; we sanitize again on the client as defense-in-depth
// (the backend isn't the only path — future edits, pasted content, etc. could
// flow through).

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

const ALLOWED_TEXT_ALIGN = new Set(['left', 'center', 'right', 'justify']);

let hooksRegistered = false;

function registerHooks(): void {
  if (hooksRegistered) return;
  hooksRegistered = true;

  // Constrain `style` to a single safe declaration: text-align with a known
  // value. Anything else (positioning, url(), expression(), etc.) is dropped.
  DOMPurify.addHook('uponSanitizeAttribute', (_node, data) => {
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
}

export function sanitizeHtml(raw: string): string {
  registerHooks();
  return DOMPurify.sanitize(raw, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
    ADD_ATTR: ['target', 'rel'],
  });
}
