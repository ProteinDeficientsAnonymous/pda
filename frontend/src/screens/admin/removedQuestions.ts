import type { Survey, SurveyResponseAdmin } from '@/api/surveyAdmin';

export interface RemovedQuestion {
  id: string;
  label: string;
}

export function removedQuestions(
  survey: Survey,
  responses: SurveyResponseAdmin[],
): RemovedQuestion[] {
  const current = new Set(survey.questions.map((q) => q.id));
  const found = new Map<string, string>();
  for (const r of responses) {
    for (const [id, entry] of Object.entries(r.answers)) {
      if (current.has(id) || found.has(id)) continue;
      found.set(id, `${storedLabel(entry) ?? 'removed question'} (removed)`);
    }
  }
  return [...found].map(([id, label]) => ({ id, label }));
}

function storedLabel(entry: unknown): string | null {
  if (typeof entry !== 'object' || entry === null) return null;
  const label = (entry as { label?: unknown }).label;
  return typeof label === 'string' && label ? label : null;
}
