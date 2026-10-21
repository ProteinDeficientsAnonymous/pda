export function attendedCountLabel(count: number): string {
  return count === 1 ? '1 event attended' : `${String(count)} events attended`;
}
