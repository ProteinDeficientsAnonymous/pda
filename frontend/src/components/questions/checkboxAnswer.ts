/** ticked options; a legacy comma-joined string is split on commas */
export function checkboxValues(answer: unknown): string[] {
  const raw = Array.isArray(answer) ? answer : typeof answer === 'string' ? answer.split(',') : [];
  return raw.map((v) => String(v).trim()).filter(Boolean);
}
