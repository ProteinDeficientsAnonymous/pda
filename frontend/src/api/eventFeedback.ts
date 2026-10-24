import { useMutation, useQuery } from '@tanstack/react-query';

import { authClient } from './client';
import { type AnswerValue, mapSurvey, type Survey, type WireSurvey } from './surveys';
import type { components } from './types.gen';

type WireEventFeedback = components['schemas']['EventFeedbackOut'];

export interface EventFeedback {
  survey: Survey | null;
  eventId: string;
  eventTitle: string;
  eventStart: Date | null;
  alreadyResponded: boolean;
  isOpen: boolean;
}

const FEEDBACK_URL = '/api/community/event-feedback/';

// authClient: public page, so no bearer and no 401-refresh handling
function tokenHeaders(token: string) {
  return { headers: { 'X-Feedback-Token': token } };
}

export function useEventFeedback(token: string) {
  return useQuery({
    queryKey: ['event-feedback', token],
    queryFn: async (): Promise<EventFeedback> => {
      const { data } = await authClient.get<WireEventFeedback>(FEEDBACK_URL, tokenHeaders(token));
      return {
        // generated feedback_event_type is a plain string; WireSurvey narrows it
        survey: data.survey ? mapSurvey(data.survey as WireSurvey) : null,
        eventId: data.event_id,
        eventTitle: data.event_title,
        eventStart: data.event_start ? new Date(data.event_start) : null,
        alreadyResponded: data.already_responded,
        isOpen: data.is_open,
      };
    },
    enabled: Boolean(token),
    retry: false,
  });
}

export function useSubmitEventFeedback(token: string) {
  return useMutation({
    mutationFn: async (answers: Record<string, AnswerValue>) => {
      const { data } = await authClient.post<{ confirmation_message: string }>(
        `${FEEDBACK_URL}respond/`,
        { answers },
        tokenHeaders(token),
      );
      return { confirmationMessage: data.confirmation_message };
    },
  });
}
