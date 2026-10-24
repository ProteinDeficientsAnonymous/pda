import { format } from 'date-fns';

import type { SurveyResponseAdmin } from '@/api/surveyAdmin';

export const ALL_EVENTS = '';

export function eventOptions(responses: SurveyResponseAdmin[]) {
  const byId = new Map<string, string>();
  for (const r of responses) {
    if (!r.eventId || byId.has(r.eventId)) continue;
    const title = r.eventTitle ?? '';
    const label = r.eventStart ? `${title} · ${format(new Date(r.eventStart), 'MMM d')}` : title;
    byId.set(r.eventId, label.toLowerCase());
  }
  return [...byId].map(([value, label]) => ({ value, label }));
}

export function filterResponsesByEvent(responses: SurveyResponseAdmin[], eventId: string) {
  return eventId === ALL_EVENTS ? responses : responses.filter((r) => r.eventId === eventId);
}

export function responseCountLabel(shown: number, total: number) {
  const noun = total === 1 ? 'response' : 'responses';
  return shown === total
    ? `${String(total)} ${noun}`
    : `${String(shown)} of ${String(total)} ${noun}`;
}
