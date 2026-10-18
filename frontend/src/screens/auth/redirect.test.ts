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

  it('keeps a query value that is already percent-encoded', () => {
    expect(safeRedirect('/events/abc?tab=guests')).toBe('/events/abc?tab=guests');
    expect(safeRedirect('/events/x?q=a%26b')).toBe('/events/x?q=a%26b');
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

  it('rejects paths the URL parser turns into a scheme-relative url', () => {
    expect(safeRedirect('/.\\\\evil.com')).toBe(DEFAULT);
    expect(safeRedirect('/a/..\\\\evil.com')).toBe(DEFAULT);
    expect(safeRedirect('/\t/x/\t/evil.com')).toBe(DEFAULT);
    expect(safeRedirect('/\t/x/\\evil.com')).toBe(DEFAULT);
  });

  it('does not preserve /members reached through dot segments', () => {
    expect(safeRedirect('/./members')).toBe(DEFAULT);
    expect(safeRedirect('/x/../members')).toBe(DEFAULT);
  });

  it('falls back when the value is not a path', () => {
    expect(safeRedirect('%')).toBe(DEFAULT);
    expect(safeRedirect('%E0%A4%A')).toBe(DEFAULT);
  });

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
