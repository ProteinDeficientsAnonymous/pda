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

  it('drops javascript: hrefs', () => {
    const out = sanitizeHtml('<a href="javascript:alert(1)">x</a>');
    expect(out).not.toContain('javascript:');
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

    it('strips non-text-align declarations', () => {
      const out = sanitizeHtml(
        '<p style="position: fixed; background: url(javascript:alert(1))">hi</p>',
      );
      expect(out).not.toContain('position');
      expect(out).not.toContain('javascript');
      expect(out).not.toContain('url(');
    });

    it('drops disallowed text-align values', () => {
      const out = sanitizeHtml('<p style="text-align: -webkit-center">hi</p>');
      expect(out).not.toContain('-webkit-center');
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
