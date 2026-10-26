import { format, isValid, parseISO } from 'date-fns';

export function renderAnswer(raw: unknown): string {
  if (raw === undefined || raw === null) return '—';
  if (typeof raw === 'object' && 'answer' in (raw as Record<string, unknown>)) {
    const a = (raw as { answer: unknown }).answer;
    if (typeof a === 'string') return a;
    // One option per line: options themselves may contain commas.
    if (Array.isArray(a)) return a.join('\n');
    if (typeof a === 'object' && a !== null) {
      return Object.entries(a as Record<string, string>)
        .map(([k, v]) => `${formatOptionKey(k)}: ${v}`)
        .join('\n');
    }
    return JSON.stringify(a);
  }
  return typeof raw === 'string' ? raw : JSON.stringify(raw);
}

// Datetime poll answers are keyed by ISO timestamps.
function formatOptionKey(key: string): string {
  if (!/^\d{4}-\d{2}-\d{2}T/.test(key)) return key;
  const d = parseISO(key);
  return isValid(d) ? format(d, 'MMM d, yyyy h:mm a').toLowerCase() : key;
}
