export function cacheBustMediaUrl(url: string, updatedAt: string | null): string {
  if (!url || !updatedAt) return url;
  if (/^https?:\/\//i.test(url)) return url;
  return `${url}?v=${encodeURIComponent(updatedAt)}`;
}
