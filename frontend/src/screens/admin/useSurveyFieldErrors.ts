import { useState } from 'react';

import { getFieldError } from '@/api/apiErrors';

import type { SurveyFormValues } from './SurveyFields';

export function useSurveyFieldErrors() {
  const [slugError, setSlugError] = useState<string | null>(null);
  const [feedbackTypeError, setFeedbackTypeError] = useState<string | null>(null);

  return {
    slugError,
    feedbackTypeError,
    reset() {
      setSlugError(null);
      setFeedbackTypeError(null);
    },
    clearFor(patch: Partial<SurveyFormValues>) {
      if ('slug' in patch) setSlugError(null);
      if ('feedbackEventType' in patch) setFeedbackTypeError(null);
    },
    capture(err: unknown): boolean {
      const slug = getFieldError(err, 'slug');
      if (slug) setSlugError(slug);
      const feedbackType = getFieldError(err, 'feedback_event_type');
      if (feedbackType) setFeedbackTypeError(feedbackType);
      return Boolean(slug ?? feedbackType);
    },
  };
}
