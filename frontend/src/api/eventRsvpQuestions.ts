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

async function createQuestion(eventId: string, q: EventRsvpQuestion): Promise<EventRsvpQuestion> {
  const { data } = await apiClient.post<WireQuestion>(
    `/api/community/events/${eventId}/rsvp-questions/`,
    {
      label: q.label,
      field_type: q.fieldType,
      options: q.options,
      required: q.required,
    },
  );
  return mapRsvpQuestion(data);
}

async function updateQuestion(eventId: string, q: EventRsvpQuestion): Promise<EventRsvpQuestion> {
  const { data } = await apiClient.patch<WireQuestion>(
    `/api/community/events/${eventId}/rsvp-questions/${q.id}/`,
    {
      label: q.label,
      field_type: q.fieldType,
      options: q.options,
      required: q.required,
    },
  );
  return mapRsvpQuestion(data);
}

async function deleteQuestion(eventId: string, questionId: string): Promise<void> {
  await apiClient.delete(`/api/community/events/${eventId}/rsvp-questions/${questionId}/`);
}

/** Sync local draft questions to the server (create / update / delete).
 * Returns the canonical list with server-assigned ids. */
export async function syncEventRsvpQuestions(
  eventId: string,
  next: readonly EventRsvpQuestion[],
  previous: readonly EventRsvpQuestion[],
): Promise<EventRsvpQuestion[]> {
  const prevIds = new Set(previous.map((q) => q.id));
  const nextIds = new Set(next.map((q) => q.id));

  // Create/update first so a later failure does not leave deletes applied
  // while the draft still expects those questions to exist.
  const synced: EventRsvpQuestion[] = [];
  for (const q of next) {
    if (prevIds.has(q.id)) {
      const before = previous.find((p) => p.id === q.id);
      if (
        before &&
        (before.label !== q.label ||
          before.fieldType !== q.fieldType ||
          before.required !== q.required ||
          JSON.stringify(before.options) !== JSON.stringify(q.options))
      ) {
        synced.push(await updateQuestion(eventId, q));
      } else {
        synced.push(q);
      }
    } else {
      synced.push(await createQuestion(eventId, q));
    }
  }

  for (const q of previous) {
    if (!nextIds.has(q.id)) {
      await deleteQuestion(eventId, q.id);
    }
  }
  return synced;
}
