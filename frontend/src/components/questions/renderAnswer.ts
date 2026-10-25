export function renderAnswer(raw: unknown): string {
  if (raw === undefined || raw === null) return '—';
  if (typeof raw === 'object' && 'answer' in (raw as Record<string, unknown>)) {
    const a = (raw as { answer: unknown }).answer;
    if (typeof a === 'string') return a;
    if (typeof a === 'object' && a !== null) {
      return Object.entries(a as Record<string, string>)
        .map(([k, v]) => `${k}: ${v}`)
        .join('\n');
    }
    return JSON.stringify(a);
  }
  return typeof raw === 'string' ? raw : JSON.stringify(raw);
}
