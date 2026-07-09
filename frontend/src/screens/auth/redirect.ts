// Open-redirect guard for the post-login `redirect` query param. Lives in its
// own module (not LoginScreen.tsx) so react-refresh stays happy — component
// files may only export components.

export const DEFAULT_POST_LOGIN_ROUTE = '/calendar';

function isNonPreservedTarget(path: string): boolean {
  const pathname = path.split(/[?#]/, 1)[0] ?? path;
  return pathname === '/members' || pathname.startsWith('/members/');
}

// Only allow relative in-app paths. Reject anything that could leave the app —
// absolute URLs (`http://evil.com`), scheme-relative URLs (`//evil.com`),
// backslash tricks (`/\evil.com`), or paths that don't start with a single
// `/`. Falls back to the default route on anything unsafe or malformed.
export function safeRedirect(raw: string | null): string {
  if (!raw) return DEFAULT_POST_LOGIN_ROUTE;
  let decoded: string;
  try {
    decoded = decodeURIComponent(raw);
  } catch {
    return DEFAULT_POST_LOGIN_ROUTE;
  }
  const isRelativePath =
    decoded.startsWith('/') && !decoded.startsWith('//') && !decoded.includes('://');
  // Normalize backslashes — some browsers treat `/\` like `//`.
  if (!isRelativePath || decoded.startsWith('/\\')) return DEFAULT_POST_LOGIN_ROUTE;
  if (isNonPreservedTarget(decoded)) return DEFAULT_POST_LOGIN_ROUTE;
  return decoded;
}
