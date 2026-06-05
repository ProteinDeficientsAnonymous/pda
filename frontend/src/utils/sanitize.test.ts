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
    // The anchor itself survives (regression guard: a config change that drops
    // <a> from ALLOWED_TAGS would lose all links and still pass a scheme-only
    // assertion).
    expect(out).toContain('<a');
    expect(out).toContain('x</a>');
  });

  it('drops protocol-relative hrefs', () => {
    const out = sanitizeHtml('<a href="//evil.com">x</a>');
    expect(out).not.toContain('evil.com');
    expect(out).not.toContain('href=');
  });

  it.each(['/\\evil.com', '\\\\evil.com', '/\\/evil.com'])(
    'drops backslash-obfuscated protocol-relative href %j',
    (href) => {
      // Browsers treat "\" as "/", so each resolves to //evil.com; the hook
      // normalises backslashes before the "//" check.
      const out = sanitizeHtml(`<a href="${href}">x</a>`);
      expect(out).not.toContain('evil.com');
      expect(out).not.toContain('href=');
    },
  );

  it('canonicalises a backslash-obfuscated scheme URL', () => {
    // "https:/\evil.com" has an allowed scheme and no literal "//"; normalise it
    // to the https://evil.com a browser resolves rather than storing the trap.
    const out = sanitizeHtml('<a href="https:/\\evil.com">x</a>');
    expect(out).toContain('href="https://evil.com"');
    expect(out).not.toContain('\\');
  });

  it('keeps https links', () => {
    const out = sanitizeHtml('<a href="https://x.test/path">x</a>');
    expect(out).toContain('href="https://x.test/path"');
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
      // The security-critical branch: the hook must rebuild the value to just the
      // safe text-align, not pass the whole attribute through because it matched.
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
