import { describe, expect, it } from 'vitest';

import { sanitizeHtml } from './sanitize';

describe('sanitizeHtml', () => {
  it('strips script tags', () => {
    const out = sanitizeHtml('<p>hi</p><script>alert(1)</script>');
    expect(out).not.toContain('<script');
    expect(out).toContain('<p>hi</p>');
  });

  it('strips inline event handlers', () => {
    const out = sanitizeHtml('<a href="https://x.test" onclick="alert(1)">x</a>');
    expect(out).not.toContain('onclick');
  });

  it('drops javascript: hrefs but keeps the link element', () => {
    const out = sanitizeHtml('<a href="javascript:alert(1)">x</a>');
    expect(out).not.toContain('javascript:');
    expect(out).not.toContain('href=');
    // Regression guard: the anchor itself must survive, not just the scheme drop.
    expect(out).toContain('<a');
    expect(out).toContain('x</a>');
  });

  it('drops protocol-relative hrefs', () => {
    const out = sanitizeHtml('<a href="//evil.com">x</a>');
    expect(out).not.toContain('evil.com');
    expect(out).not.toContain('href=');
  });

  it.each([
    '/\\evil.com', // backslash — browsers normalise /\ to //
    '\\\\evil.com', // double backslash
    '/\\/evil.com', // mixed
    '/\t/evil.com', // tab BETWEEN the slashes (browsers strip it -> //)
    '/\t\t/evil.com', // multiple embedded tabs
    '/\n/evil.com', // embedded newline
    '///evil.com', // 3+ leading slashes — browsers read authority
    '////evil.com', // 4 leading slashes
  ])('drops obfuscated protocol-relative href %j', (href) => {
    const out = sanitizeHtml(`<a href="${href}">x</a>`);
    expect(out).not.toContain('evil.com');
    expect(out).not.toContain('href=');
  });

  it('canonicalises a backslash-obfuscated scheme URL', () => {
    const out = sanitizeHtml('<a href="https:/\\evil.com">x</a>');
    expect(out).toContain('href="https://evil.com"');
    expect(out).not.toContain('\\');
  });

  it('preserves a legitimate backslash in a query string', () => {
    const out = sanitizeHtml('<a href="https://good.com/p?x=a\\b">y</a>');
    expect(out).toContain('x=a\\b');
  });

  it('keeps https links', () => {
    const out = sanitizeHtml('<a href="https://x.test/path">x</a>');
    expect(out).toContain('href="https://x.test/path"');
  });

  it.each([
    '<img src="data:image/svg+xml,<svg onload=alert(1)>">',
    '<img src="data:image/png;base64,AAAA">',
    '<img src="mailto:a@b.test">',
  ])('drops non-http(s) image src %j', (html) => {
    const out = sanitizeHtml(html);
    expect(out).not.toContain('data:');
    expect(out).not.toContain('mailto:');
    expect(out).not.toContain('src=');
  });

  it('keeps https and relative image src', () => {
    const out = sanitizeHtml('<img src="https://x.test/a.png"><img src="/media/b.jpg">');
    expect(out).toContain('src="https://x.test/a.png"');
    expect(out).toContain('src="/media/b.jpg"');
  });

  describe('style attribute', () => {
    it('keeps text-align declarations', () => {
      const out = sanitizeHtml('<p style="text-align: center">hi</p>');
      expect(out).toContain('text-align: center');
    });

    it('drops a style with no text-align entirely', () => {
      const out = sanitizeHtml(
        '<p style="position: fixed; background: url(javascript:alert(1))">hi</p>',
      );
      expect(out).not.toContain('position');
      expect(out).not.toContain('javascript');
      expect(out).not.toContain('url(');
      expect(out).not.toContain('style=');
    });

    it('keeps valid text-align while stripping a malicious sibling declaration', () => {
      const out = sanitizeHtml('<p style="text-align: center; position: fixed; top: 0">hi</p>');
      expect(out).toContain('text-align: center');
      expect(out).not.toContain('position');
      expect(out).not.toContain('fixed');
    });

    it('drops disallowed text-align values', () => {
      const out = sanitizeHtml('<p style="text-align: -webkit-center">hi</p>');
      expect(out).not.toContain('-webkit-center');
      expect(out).not.toContain('style=');
    });

    it('drops justify (renderers only emit left/center/right)', () => {
      const out = sanitizeHtml('<p style="text-align: justify">hi</p>');
      expect(out).not.toContain('justify');
      expect(out).not.toContain('style=');
    });

    it('drops a prefixed text-align property', () => {
      const out = sanitizeHtml('<p style="-webkit-text-align: right">hi</p>');
      expect(out).not.toContain('style=');
    });
  });

  describe('rel on target=_blank links', () => {
    it('forces rel=noopener noreferrer when target is _blank', () => {
      const out = sanitizeHtml('<a href="https://x.test" target="_blank">x</a>');
      expect(out).toContain('rel="noopener noreferrer"');
    });

    it('overrides an attacker-supplied rel', () => {
      const out = sanitizeHtml('<a href="https://x.test" target="_blank" rel="opener">x</a>');
      expect(out).toContain('rel="noopener noreferrer"');
      expect(out).not.toContain('rel="opener"');
    });

    it('does not add rel to non-blank links', () => {
      const out = sanitizeHtml('<a href="https://x.test">x</a>');
      expect(out).not.toContain('noopener');
    });
  });
});
