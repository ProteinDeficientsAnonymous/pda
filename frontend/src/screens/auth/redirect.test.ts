// Open-redirect guard for the post-login `redirect` query param.
import { describe, expect, it } from 'vitest';

import { safeRedirect } from './redirect';

const DEFAULT = '/calendar';

describe('safeRedirect', () => {
  it('falls back to the default route when no redirect is given', () => {
    expect(safeRedirect(null)).toBe(DEFAULT);
    expect(safeRedirect('')).toBe(DEFAULT);
  });

  it('allows a plain relative in-app path', () => {
    expect(safeRedirect('/events/abc123')).toBe('/events/abc123');
    expect(safeRedirect('/admin/members')).toBe('/admin/members');
  });

  it('decodes percent-encoded relative paths', () => {
    expect(safeRedirect(encodeURIComponent('/events/abc?tab=guests'))).toBe(
      '/events/abc?tab=guests',
    );
  });

  it('rejects scheme-relative urls (//evil.com)', () => {
    expect(safeRedirect('//evil.com')).toBe(DEFAULT);
    expect(safeRedirect(encodeURIComponent('//evil.com'))).toBe(DEFAULT);
  });

  it('rejects absolute urls with a scheme', () => {
    expect(safeRedirect('https://evil.com')).toBe(DEFAULT);
    expect(safeRedirect('http://evil.com/path')).toBe(DEFAULT);
    expect(safeRedirect('javascript://alert(1)')).toBe(DEFAULT);
  });

  it('rejects paths that do not start with a single slash', () => {
    expect(safeRedirect('evil.com')).toBe(DEFAULT);
    expect(safeRedirect('calendar')).toBe(DEFAULT);
  });

  it('rejects backslash tricks (/\\evil.com)', () => {
    expect(safeRedirect('/\\evil.com')).toBe(DEFAULT);
  });

  it('falls back when decoding throws on a malformed escape', () => {
    expect(safeRedirect('%')).toBe(DEFAULT);
    expect(safeRedirect('%E0%A4%A')).toBe(DEFAULT);
  });

  // Issue 479: /members is a low-value bounce target — a fresh login should
  // land on the calendar rather than the member directory.
  it('does not preserve /members or its subpaths', () => {
    expect(safeRedirect('/members')).toBe(DEFAULT);
    expect(safeRedirect('/members/abc123')).toBe(DEFAULT);
    expect(safeRedirect('/members?tab=all')).toBe(DEFAULT);
    expect(safeRedirect(encodeURIComponent('/members/abc123'))).toBe(DEFAULT);
  });

  it('still preserves /admin/members (a different route)', () => {
    expect(safeRedirect('/admin/members')).toBe('/admin/members');
  });
});
