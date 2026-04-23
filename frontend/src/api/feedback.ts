// Feedback submission — POST /api/community/feedback/.
//
// Backend creates a GitHub issue via the GitHub App. Returns { html_url } on
// success (201). A 503 is returned when the GitHub App isn't configured; from
// the user's perspective both failure modes surface the same toast.

import { useMutation } from '@tanstack/react-query';
import { apiClient } from './client';

export type FeedbackType = 'bug' | 'feature request';

export interface SubmitFeedbackPayload {
  title: string;
  description: string;
  feedbackTypes: FeedbackType[];
  metadata: {
    route: string;
    userAgent: string;
    userDisplayName: string;
    appVersion: string;
  };
}

export interface FeedbackOut {
  html_url: string;
}

export function useSubmitFeedback() {
  return useMutation({
    mutationFn: async (payload: SubmitFeedbackPayload) => {
      const { data } = await apiClient.post<FeedbackOut>('/api/community/feedback/', {
        title: payload.title,
        description: payload.description,
        feedback_types: payload.feedbackTypes,
        metadata: {
          route: payload.metadata.route,
          user_agent: payload.metadata.userAgent,
          user_display_name: payload.metadata.userDisplayName,
          app_version: payload.metadata.appVersion,
        },
      });
      return data;
    },
  });
}
