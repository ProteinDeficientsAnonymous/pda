export const DEFAULT_POST_LOGIN_ROUTE = '/calendar';

function isNonPreservedTarget(path: string): boolean {
  const pathname = path.split(/[?#]/, 1)[0] ?? path;
  return pathname === '/members' || pathname.startsWith('/members/');
}

// Only allow a same-origin relative path. Callers pass the value
// URLSearchParams already decoded, so this does not decode again. The URL
// parser folds backslash, dot-segment, and tab/newline tricks into the path
// the browser would use.
export function safeRedirect(raw: string | null): string {
  if (!raw) return DEFAULT_POST_LOGIN_ROUTE;
  if (!raw.startsWith('/') || raw.startsWith('//') || raw.includes('://')) {
    return DEFAULT_POST_LOGIN_ROUTE;
  }
  let url: URL;
  try {
    url = new URL(raw, window.location.origin);
  } catch {
    return DEFAULT_POST_LOGIN_ROUTE;
  }
  if (url.origin !== window.location.origin || url.pathname.startsWith('//')) {
    return DEFAULT_POST_LOGIN_ROUTE;
  }
  const target = `${url.pathname}${url.search}${url.hash}`;
  if (isNonPreservedTarget(target)) return DEFAULT_POST_LOGIN_ROUTE;
  return target;
}
