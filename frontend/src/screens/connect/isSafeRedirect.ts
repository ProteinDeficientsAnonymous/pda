const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '::1']);

// backend sends urlparse().hostname (no port, no ipv6 brackets), so compare hostnames
export function isSafeRedirect(raw: string, expectedHost: string): boolean {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return false;
  }
  const hostname = url.hostname.replace(/^\[|\]$/g, '').toLowerCase();
  if (!hostname || hostname !== expectedHost.toLowerCase()) return false;
  if (url.protocol === 'https:') return true;
  return url.protocol === 'http:' && LOOPBACK_HOSTS.has(hostname);
}
