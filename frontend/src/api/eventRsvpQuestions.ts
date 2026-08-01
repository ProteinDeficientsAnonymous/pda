import type { EventRsvpQuestion, EventRsvpQuestionType } from '@/models/event';

import { apiClient } from './client';

interface WireQuestion {
  id: string;
  label: string;
  field_type: EventRsvpQuestionType;
  options: string[];
  required: boolean;
  display_order: number;
}

export function mapRsvpQuestion(w: WireQuestion): EventRsvpQuestion {
  return {
    id: w.id,
    label: w.label,
    fieldType: w.field_type,
    options: w.options,
    required: w.required,
  };
}

function questionPayload(question: EventRsvpQuestion, newIdsAsNull: boolean) {
  return {
    id: newIdsAsNull && question.id.startsWith('q-') ? null : question.id,
    label: question.label,
    field_type: question.fieldType,
    options: question.options,
    required: question.required,
  };
}

/** Replace questions atomically and return canonical server ids/order. */
export async function syncEventRsvpQuestions(
  eventId: string,
  next: readonly EventRsvpQuestion[],
  previous: readonly EventRsvpQuestion[],
): Promise<EventRsvpQuestion[]> {
  const { data } = await apiClient.put<WireQuestion[]>(
    `/api/community/events/${eventId}/rsvp-questions/`,
    {
      expected: previous.map((question) => questionPayload(question, false)),
      questions: next.map((question) => questionPayload(question, true)),
    },
  );
  return data.map(mapRsvpQuestion);
}
