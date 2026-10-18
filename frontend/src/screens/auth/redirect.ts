export const DEFAULT_POST_LOGIN_ROUTE = '/calendar';

function isNonPreservedTarget(path: string): boolean {
  const pathname = path.split(/[?#]/, 1)[0] ?? path;
  return pathname === '/members' || pathname.startsWith('/members/');
}

// Only allow a same-origin relative path. The URL parser folds backslash,
// dot-segment, and tab/newline tricks into the path the browser would use.
// Falls back to the default route when that path is off-site or malformed.
export function safeRedirect(raw: string | null): string {
  if (!raw) return DEFAULT_POST_LOGIN_ROUTE;
  let decoded: string;
  try {
    decoded = decodeURIComponent(raw);
  } catch {
    return DEFAULT_POST_LOGIN_ROUTE;
  }
  if (!decoded.startsWith('/') || decoded.startsWith('//') || decoded.includes('://')) {
    return DEFAULT_POST_LOGIN_ROUTE;
  }
  let url: URL;
  try {
    url = new URL(decoded, window.location.origin);
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
