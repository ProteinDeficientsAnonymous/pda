import { describe, expect, it } from 'vitest';

import { isSafeRedirect } from './isSafeRedirect';

describe('isSafeRedirect', () => {
  it.each([
    ['https://claude.ai/api/mcp/auth_callback?code=x&state=y', 'claude.ai'],
    ['https://Claude.AI/cb', 'claude.ai'],
    ['http://localhost:6274/oauth/callback', 'localhost'],
    ['http://127.0.0.1:8080/cb', '127.0.0.1'],
    ['http://[::1]:8080/cb', '::1'],
  ])('allows %s', (url, host) => {
    expect(isSafeRedirect(url, host)).toBe(true);
  });

  it.each([
    ['http://example.com/cb', 'example.com'],
    ['javascript:alert(1)', ''],
    ['data:text/html,<script>alert(1)</script>', ''],
    ['claude://callback', 'callback'],
    ['/relative/path', ''],
    ['not a url', ''],
    ['', ''],
  ])('rejects unsafe or malformed %s', (url, host) => {
    expect(isSafeRedirect(url, host)).toBe(false);
  });

  it('rejects a host that differs from the one shown', () => {
    expect(isSafeRedirect('https://evil.example/cb', 'claude.ai')).toBe(false);
  });
});
